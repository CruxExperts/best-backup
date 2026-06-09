"""
Encryption module for bbackup.
Handles symmetric (AES-256-GCM) and asymmetric (RSA/ECDSA) encryption.
Supports URL-based key fetching for easy multi-server deployment.
"""

import os
import hashlib
import json
from pathlib import Path
from typing import Optional, Tuple, Any
from datetime import datetime
import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import secrets

from .logging import get_logger

logger = get_logger('encryption')


class EncryptionManager:
    """Main encryption manager for backup encryption/decryption."""
    
    def __init__(self, encryption_config: Any):
        """
        Initialize encryption manager.
        
        Args:
            encryption_config: EncryptionSettings dataclass from config
        """
        self.config = encryption_config
        self.symmetric_key: Optional[bytes] = None
        self.public_key: Optional[Any] = None
        self.private_key: Optional[Any] = None
        
        # Load keys based on configuration
        if encryption_config.method in ['symmetric', 'both']:
            self.symmetric_key = self._load_symmetric_key()
        
        if encryption_config.method in ['asymmetric', 'both']:
            self.public_key = self._load_public_key()
            self.private_key = self._load_private_key()
    
    def _load_symmetric_key(self) -> Optional[bytes]:
        """Load symmetric key from file or URL."""
        key_source = self.config.symmetric.get('key_file') or self.config.symmetric.get('key_url')
        if not key_source:
            logger.error("Symmetric key file or URL not configured")
            return None
        
        password = self.config.symmetric.get('key_password')
        
        try:
            # Check for GitHub shortcut
            if self._is_github_shortcut(key_source):
                resolved_url = self._resolve_github_key_url(key_source)
                if not resolved_url:
                    logger.error(f"Could not resolve GitHub shortcut: {key_source}")
                    return None
                key_data = self._fetch_key_from_url(resolved_url)
            elif self._is_url(key_source):
                key_data = self._fetch_key_from_url(key_source)
            else:
                key_path = Path(key_source).expanduser()
                if not key_path.exists():
                    logger.error(f"Symmetric key file not found: {key_path}")
                    return None
                key_data = key_path.read_bytes()
            
            # If password provided, derive key using PBKDF2
            if password:
                salt = key_data[:16]  # First 16 bytes as salt
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                    backend=default_backend()
                )
                return kdf.derive(password.encode())
            else:
                # Use key directly (should be 32 bytes for AES-256)
                if len(key_data) < 32:
                    logger.warning(f"Key too short ({len(key_data)} bytes), padding to 32 bytes")
                    key_data = key_data.ljust(32, b'\0')
                elif len(key_data) > 32:
                    logger.warning(f"Key too long ({len(key_data)} bytes), truncating to 32 bytes")
                    key_data = key_data[:32]
                return key_data
        except Exception as e:
            logger.error(f"Failed to load symmetric key: {e}")
            return None
    
    def _load_public_key(self) -> Optional[Any]:
        """Load public key from file or URL."""
        key_source = self.config.asymmetric.get('public_key')
        if not key_source:
            logger.error("Public key file or URL not configured")
            return None
        
        try:
            # Check for GitHub shortcut
            if self._is_github_shortcut(key_source):
                resolved_url = self._resolve_github_key_url(key_source)
                if not resolved_url:
                    logger.error(f"Could not resolve GitHub shortcut: {key_source}")
                    return None
                key_data = self._fetch_key_from_url(resolved_url)
            elif self._is_url(key_source):
                key_data = self._fetch_key_from_url(key_source)
            else:
                key_path = Path(key_source).expanduser()
                if not key_path.exists():
                    logger.error(f"Public key file not found: {key_path}")
                    return None
                key_data = key_path.read_bytes()
            
            # Validate key format
            if not self._validate_key_format(key_data, 'public'):
                logger.error("Invalid public key format")
                return None
            
            # Load public key
            public_key = serialization.load_pem_public_key(key_data, backend=default_backend())
            logger.info("Public key loaded successfully")
            return public_key
        except Exception as e:
            logger.error(f"Failed to load public key: {e}")
            return None
    
    def _load_private_key(self) -> Optional[Any]:
        """Load private key from local file (never from URL for security)."""
        key_path_str = self.config.asymmetric.get('private_key')
        if not key_path_str:
            logger.error("Private key file not configured")
            return None
        
        key_path = Path(key_path_str).expanduser()
        if not key_path.exists():
            logger.error(f"Private key file not found: {key_path}")
            return None
        
        # Security check: private keys must be local files
        if self._is_url(key_path_str):
            logger.error("Private keys cannot be loaded from URLs (security risk)")
            return None
        
        password = self.config.asymmetric.get('private_key_password')
        password_bytes = password.encode() if password else None
        
        try:
            key_data = key_path.read_bytes()
            
            # Validate key format
            if not self._validate_key_format(key_data, 'private'):
                logger.error("Invalid private key format")
                return None
            
            # Load private key
            private_key = serialization.load_pem_private_key(
                key_data,
                password=password_bytes,
                backend=default_backend()
            )
            logger.info("Private key loaded successfully")
            return private_key
        except Exception as e:
            logger.error(f"Failed to load private key: {e}")
            return None
    
    def _is_url(self, source: str) -> bool:
        """Check if source is a URL."""
        return source.startswith('http://') or source.startswith('https://')
    
    def _is_github_shortcut(self, source: str) -> bool:
        """Check if source is a GitHub username shortcut."""
        return source.startswith('github:') or source.startswith('gh:')
    
    def _resolve_github_key_url(self, shortcut: str) -> Optional[str]:
        """
        Resolve GitHub username shortcut to actual key URL.
        
        Supports formats:
        - github:USERNAME
        - gh:USERNAME
        - github:USERNAME/gist:GIST_ID
        - github:USERNAME/repo:REPO_NAME
        
        Tries multiple strategies:
        1. If gist/repo specified, use that
        2. Try standard gist name: bbackup-keys
        3. Try standard repo: backup-keys or bbackup-keys
        4. Try SSH keys endpoint (as fallback)
        
        Args:
            shortcut: GitHub shortcut (e.g., "github:USERNAME")
        
        Returns:
            Resolved URL or None if not found
        """
        # Parse shortcut
        if shortcut.startswith('github:'):
            username = shortcut[7:]  # Remove "github:"
        elif shortcut.startswith('gh:'):
            username = shortcut[3:]  # Remove "gh:"
        else:
            return None
        
        # Check for explicit gist/repo specification
        if '/gist:' in username:
            username, gist_id = username.split('/gist:', 1)
            return f"https://gist.githubusercontent.com/{username}/{gist_id}/raw/backup_public.pem"
        
        if '/repo:' in username:
            username, repo_name = username.split('/repo:', 1)
            return f"https://raw.githubusercontent.com/{username}/{repo_name}/main/backup_public.pem"
        
        # Strategy 1: Try standard gist name "bbackup-keys"
        # Note: We can't list gists via API without auth, so we'll try common patterns
        standard_gist_urls = [
            f"https://gist.githubusercontent.com/{username}/bbackup-keys/raw/backup_public.pem",
            f"https://gist.githubusercontent.com/{username}/backup-keys/raw/backup_public.pem",
        ]
        
        # Strategy 2: Try standard repository names
        standard_repo_urls = [
            f"https://raw.githubusercontent.com/{username}/bbackup-keys/main/backup_public.pem",
            f"https://raw.githubusercontent.com/{username}/backup-keys/main/backup_public.pem",
            f"https://raw.githubusercontent.com/{username}/bbackup-keys/master/backup_public.pem",
            f"https://raw.githubusercontent.com/{username}/backup-keys/master/backup_public.pem",
        ]
        
        # Try all strategies in order
        all_urls = standard_gist_urls + standard_repo_urls
        
        logger.info(f"Resolving GitHub shortcut: {shortcut}")
        logger.info(f"Trying {len(all_urls)} potential URLs...")
        
        for url in all_urls:
            try:
                response = requests.head(url, timeout=5, verify=True, allow_redirects=True)
                if response.status_code == 200:
                    logger.info(f"Found key at: {url}")
                    return url
            except requests.RequestException:
                continue
        
        # Strategy 3: Fallback to SSH keys (inform user they need to convert)
        logger.warning(f"Could not find standard key locations for {username}")
        logger.info("Trying SSH keys endpoint as fallback...")
        ssh_keys_url = f"https://github.com/{username}.keys"
        
        try:
            response = requests.head(ssh_keys_url, timeout=5, verify=True)
            if response.status_code == 200:
                logger.warning(f"Found SSH keys at {ssh_keys_url}, but these may need conversion to PEM format")
                logger.info("Consider creating a gist or repo with your RSA public key in PEM format")
                # Return SSH keys URL as fallback (user will need to handle conversion)
                return ssh_keys_url
        except requests.RequestException:
            pass
        
        logger.error(f"Could not resolve GitHub shortcut: {shortcut}")
        logger.info("Suggestions:")
        logger.info("  1. Create a gist named 'bbackup-keys' with your public key")
        logger.info("  2. Create a repo named 'bbackup-keys' with backup_public.pem")
        logger.info(f"  3. Use explicit format: github:{username}/gist:GIST_ID")
        logger.info(f"  4. Use explicit format: github:{username}/repo:REPO_NAME")
        
        return None
    
    def _fetch_key_from_url(self, url: str, verify_https: bool = True) -> bytes:
        """
        Fetch key from URL with validation.
        
        Args:
            url: URL to fetch key from
            verify_https: Require HTTPS (security)
        
        Returns:
            Key data as bytes
        """
        # Security: Require HTTPS
        if verify_https and not url.startswith('https://'):
            raise ValueError(f"Only HTTPS URLs allowed for key fetching: {url}")
        
        try:
            logger.info(f"Fetching key from URL: {url}")
            response = requests.get(url, timeout=10, verify=True)
            response.raise_for_status()
            
            key_data = response.content
            
            # Validate key format (basic check)
            if len(key_data) == 0:
                raise ValueError("Empty key data from URL")
            
            # Cache key locally for offline use
            self._cache_key(url, key_data)
            
            logger.info(f"Successfully fetched key from URL ({len(key_data)} bytes)")
            return key_data
        except requests.RequestException as e:
            logger.error(f"Failed to fetch key from URL {url}: {e}")
            # Try to load from cache
            cached_key = self._load_cached_key(url)
            if cached_key:
                logger.info("Using cached key")
                return cached_key
            raise
    
    def _cache_key(self, url: str, key_data: bytes) -> None:
        """Cache downloaded key locally."""
        cache_dir = Path.home() / '.cache' / 'bbackup' / 'keys'
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Create cache filename from URL hash
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        cache_file = cache_dir / f"key_{url_hash}.cache"
        
        try:
            cache_file.write_bytes(key_data)
            cache_file.chmod(0o600)  # Secure permissions
            logger.debug(f"Cached key to {cache_file}")
        except Exception as e:
            logger.warning(f"Failed to cache key: {e}")
    
    def _load_cached_key(self, url: str) -> Optional[bytes]:
        """Load cached key if available."""
        cache_dir = Path.home() / '.cache' / 'bbackup' / 'keys'
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        cache_file = cache_dir / f"key_{url_hash}.cache"
        
        if cache_file.exists():
            try:
                return cache_file.read_bytes()
            except Exception as e:
                logger.warning(f"Failed to load cached key: {e}")
        
        return None
    
    def _validate_key_format(self, key_data: bytes, key_type: str) -> bool:
        """
        Validate key format.
        
        Args:
            key_data: Key data bytes
            key_type: 'public' or 'private'
        
        Returns:
            True if valid format
        """
        try:
            key_str = key_data.decode('utf-8', errors='ignore')
            
            if key_type == 'public':
                # Check for PEM public key markers
                return '-----BEGIN PUBLIC KEY-----' in key_str or \
                       '-----BEGIN RSA PUBLIC KEY-----' in key_str
            elif key_type == 'private':
                # Check for PEM private key markers
                return '-----BEGIN PRIVATE KEY-----' in key_str or \
                       '-----BEGIN RSA PRIVATE KEY-----' in key_str or \
                       '-----BEGIN ENCRYPTED PRIVATE KEY-----' in key_str
            else:
                return False
        except Exception:
            return False
    
    def encrypt_file(self, source: Path, dest: Path, key: Optional[bytes] = None) -> bool:
        """
        Encrypt a file using AES-256-GCM.
        For asymmetric encryption, generates a session key and encrypts it with the public key.
        
        Args:
            source: Source file path
            dest: Destination encrypted file path
            key: Encryption key (uses symmetric_key if None, or generates session key for asymmetric)
        
        Returns:
            True if successful
        """
        # Determine encryption key based on method
        if key is None:
            if self.config.method in ['symmetric', 'both'] and self.symmetric_key:
                key = self.symmetric_key
            elif self.config.method in ['asymmetric', 'both'] and self.public_key:
                # Generate session key for asymmetric encryption
                key = secrets.token_bytes(32)  # 32 bytes for AES-256
            else:
                logger.error("No encryption key available")
                return False
        
        if key is None:
            logger.error("No encryption key available")
            return False
        
        try:
            # Read source file
            plaintext = source.read_bytes()
            
            # Generate random IV (12 bytes for GCM)
            iv = secrets.token_bytes(12)
            
            # Encrypt with AES
            aesgcm = AESGCM(key)
            ciphertext = aesgcm.encrypt(iv, plaintext, None)
            
            # For asymmetric encryption, encrypt the session key with public key
            encrypted_key = None
            if self.config.method in ['asymmetric', 'both'] and self.public_key and key != self.symmetric_key:
                try:
                    # Encrypt session key with public key
                    encrypted_key = self.public_key.encrypt(
                        key,
                        padding.OAEP(
                            mgf=padding.MGF1(algorithm=hashes.SHA256()),
                            algorithm=hashes.SHA256(),
                            label=None
                        )
                    )
                except Exception as e:
                    logger.error(f"Failed to encrypt session key: {e}")
                    return False
            
            # Write encrypted file
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, 'wb') as f:
                # Format: [encrypted_key_length (4 bytes)] [encrypted_key] [IV (12 bytes)] [ciphertext]
                if encrypted_key:
                    f.write(len(encrypted_key).to_bytes(4, 'big'))
                    f.write(encrypted_key)
                f.write(iv)
                f.write(ciphertext)
            
            logger.debug(f"Encrypted file: {source} -> {dest}")
            return True
        except Exception as e:
            logger.error(f"Failed to encrypt file {source}: {e}")
            return False
    
    def decrypt_file(self, source: Path, dest: Path, key: Optional[bytes] = None) -> bool:
        """
        Decrypt a file encrypted with AES-256-GCM.
        For asymmetric encryption, decrypts the session key with the private key first.
        
        Args:
            source: Encrypted file path
            dest: Destination decrypted file path
            key: Decryption key (uses symmetric_key if None, or decrypts session key for asymmetric)
        
        Returns:
            True if successful
        """
        try:
            # Read encrypted file
            encrypted_data = source.read_bytes()
            
            if len(encrypted_data) < 12:
                logger.error("Encrypted file too short (missing IV)")
                return False
            
            # Check if file has encrypted session key (asymmetric encryption)
            offset = 0
            if self.config.method in ['asymmetric', 'both'] and self.private_key:
                # Try to read encrypted key length (first 4 bytes)
                if len(encrypted_data) >= 4:
                    key_length = int.from_bytes(encrypted_data[:4], 'big')
                    # Reasonable key length check (RSA-4096 encrypted key is 512 bytes)
                    if 0 < key_length < 1024 and len(encrypted_data) >= 4 + key_length + 12:
                        try:
                            # Extract and decrypt session key
                            encrypted_key = encrypted_data[4:4+key_length]
                            key = self.private_key.decrypt(
                                encrypted_key,
                                padding.OAEP(
                                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                                    algorithm=hashes.SHA256(),
                                    label=None
                                )
                            )
                            offset = 4 + key_length
                            logger.debug("Decrypted session key for asymmetric encryption")
                        except Exception as e:
                            # Not an asymmetric-encrypted file, try symmetric
                            logger.debug(f"Not asymmetric-encrypted file (trying symmetric): {e}")
                            offset = 0
                            pass
            
            # If no key yet, use symmetric key
            if key is None:
                if self.config.method in ['symmetric', 'both'] and self.symmetric_key:
                    key = self.symmetric_key
                else:
                    logger.error("No decryption key available")
                    return False
            
            if key is None:
                logger.error("No decryption key available")
                return False
            
            # Extract IV and ciphertext
            if len(encrypted_data) < offset + 12:
                logger.error("Encrypted file too short (missing IV)")
                return False
            
            iv = encrypted_data[offset:offset+12]
            ciphertext = encrypted_data[offset+12:]
            
            # Decrypt
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(iv, ciphertext, None)
            
            # Write decrypted file
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(plaintext)
            
            logger.debug(f"Decrypted file: {source} -> {dest}")
            return True
        except Exception as e:
            logger.error(f"Failed to decrypt file {source}: {e}")
            return False
    
    def encrypt_directory(self, source: Path, dest: Path) -> bool:
        """
        Encrypt all files in a directory.
        
        Args:
            source: Source directory
            dest: Destination directory (will contain encrypted files)
        
        Returns:
            True if successful
        """
        try:
            dest.mkdir(parents=True, exist_ok=True)
            
            # Create encryption metadata
            metadata = {
                "encrypted": True,
                "method": self.config.method,
                "algorithm": "aes-256-gcm",
                "key_id": hashlib.sha256(self.symmetric_key or b'').hexdigest()[:16] if self.symmetric_key else None,
                "timestamp": datetime.now().isoformat()
            }
            
            # Encrypt all files
            for root, dirs, files in os.walk(source):
                for file in files:
                    source_file = Path(root) / file
                    rel_path = source_file.relative_to(source)
                    dest_file = dest / f"{rel_path}.enc"
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    if not self.encrypt_file(source_file, dest_file):
                        return False
            
            # Save metadata
            metadata_file = dest / "encryption_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Encrypted directory: {source} -> {dest}")
            return True
        except Exception as e:
            logger.error(f"Failed to encrypt directory {source}: {e}")
            return False
    
    def decrypt_directory(self, source: Path, dest: Path) -> bool:
        """
        Decrypt all files in an encrypted directory.
        
        Args:
            source: Encrypted directory
            dest: Destination directory (will contain decrypted files)
        
        Returns:
            True if successful
        """
        try:
            dest.mkdir(parents=True, exist_ok=True)
            
            # Check for metadata
            metadata_file = source / "encryption_metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    logger.info(f"Decrypting backup encrypted with method: {metadata.get('method')}")
            
            # Decrypt all .enc files
            for root, dirs, files in os.walk(source):
                for file in files:
                    if file == "encryption_metadata.json":
                        continue
                    
                    if file.endswith('.enc'):
                        source_file = Path(root) / file
                        rel_path = source_file.relative_to(source)
                        # Remove .enc extension
                        dest_rel_path = str(rel_path)[:-4]  # Remove .enc
                        dest_file = dest / dest_rel_path
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        
                        if not self.decrypt_file(source_file, dest_file):
                            return False
            
            logger.info(f"Decrypted directory: {source} -> {dest}")
            return True
        except Exception as e:
            logger.error(f"Failed to decrypt directory {source}: {e}")
            return False
    
    def encrypt_backup(self, backup_dir: Path) -> Path:
        """
        Encrypt entire backup directory.
        
        Args:
            backup_dir: Backup directory to encrypt
        
        Returns:
            Path to encrypted backup directory
        """
        encrypted_dir = backup_dir.parent / f"{backup_dir.name}.enc"
        
        if self.encrypt_directory(backup_dir, encrypted_dir):
            return encrypted_dir
        else:
            logger.error("Failed to encrypt backup")
            return backup_dir  # Return original on failure
    
    def decrypt_backup(self, backup_dir: Path) -> Path:
        """
        Decrypt entire backup directory.
        
        Args:
            backup_dir: Encrypted backup directory
        
        Returns:
            Path to decrypted backup directory
        """
        # Check if already decrypted
        if not (backup_dir / "encryption_metadata.json").exists():
            logger.info("Backup appears to be unencrypted")
            return backup_dir
        
        decrypted_dir = backup_dir.parent / backup_dir.name.replace('.enc', '')
        
        if self.decrypt_directory(backup_dir, decrypted_dir):
            return decrypted_dir
        else:
            logger.error("Failed to decrypt backup")
            return backup_dir  # Return original on failure
    
    @staticmethod
    def generate_symmetric_key() -> bytes:
        """Generate a random symmetric key (32 bytes for AES-256)."""
        return secrets.token_bytes(32)
    
    @staticmethod
    def generate_keypair(algorithm: str = 'rsa-4096') -> Tuple[bytes, bytes]:
        """
        Generate asymmetric keypair.
        
        Args:
            algorithm: 'rsa-4096'
        
        Returns:
            Tuple of (public_key_bytes, private_key_bytes) in PEM format
        """
        if algorithm == 'rsa-4096':
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=4096,
                backend=default_backend()
            )
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        public_key = private_key.public_key()
        
        # Serialize to PEM
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return public_pem, private_pem
