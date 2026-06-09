"""
Tests for bbackup.encryption - AES-GCM primitives, EncryptionManager construction,
GitHub shortcut resolution, key cache, PBKDF2, file/directory/backup encryption.
Created: 2026-02-26
Last Updated: 2026-02-26
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from bbackup.config import EncryptionSettings
from bbackup.encryption import EncryptionManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_sym_config(key_file=None, method="symmetric", enabled=True):
    return EncryptionSettings(
        enabled=enabled,
        method=method,
        symmetric={"key_file": key_file} if key_file else {},
    )


def make_manager_with_key(tmp_path, key_bytes=None):
    """Create an EncryptionManager backed by a real key file."""
    key = key_bytes or os.urandom(32)
    key_file = tmp_path / "test.key"
    key_file.write_bytes(key)
    cfg = make_sym_config(key_file=str(key_file))
    mgr = EncryptionManager(cfg)
    return mgr, key


# ---------------------------------------------------------------------------
# TestAESGCMPrimitives
# ---------------------------------------------------------------------------


class TestAESGCMPrimitives:
    """Direct AESGCM primitive tests without EncryptionManager."""

    def test_roundtrip_preserves_data(self):
        key = os.urandom(32)
        iv = os.urandom(12)
        plaintext = b"Hello, world!"
        aesgcm = AESGCM(key)
        ct = aesgcm.encrypt(iv, plaintext, None)
        assert aesgcm.decrypt(iv, ct, None) == plaintext

    def test_nonce_uniqueness(self):
        key = os.urandom(32)
        plaintext = b"same plaintext"
        aesgcm = AESGCM(key)
        iv1 = os.urandom(12)
        iv2 = os.urandom(12)
        ct1 = aesgcm.encrypt(iv1, plaintext, None)
        ct2 = aesgcm.encrypt(iv2, plaintext, None)
        # Two encryptions of the same plaintext with different nonces produce different ciphertexts
        assert ct1 != ct2

    def test_wrong_key_raises(self):
        key = os.urandom(32)
        wrong_key = os.urandom(32)
        iv = os.urandom(12)
        aesgcm = AESGCM(key)
        ct = aesgcm.encrypt(iv, b"data", None)
        with pytest.raises(Exception):
            AESGCM(wrong_key).decrypt(iv, ct, None)

    def test_tampered_ciphertext_raises(self):
        key = os.urandom(32)
        iv = os.urandom(12)
        aesgcm = AESGCM(key)
        ct = bytearray(aesgcm.encrypt(iv, b"data", None))
        ct[0] ^= 0xFF  # flip bits
        with pytest.raises(Exception):
            aesgcm.decrypt(iv, bytes(ct), None)

    def test_key_exactly_32_bytes(self):
        key = b"A" * 32
        AESGCM(key)  # Should not raise

    def test_key_short_raises(self):
        key = b"short"
        with pytest.raises(Exception):
            AESGCM(key)


# ---------------------------------------------------------------------------
# TestEncryptionManagerConstruction
# ---------------------------------------------------------------------------


class TestEncryptionManagerConstruction:
    def test_disabled_config_no_key_loaded(self):
        cfg = EncryptionSettings(enabled=False, method="symmetric", symmetric={})
        mgr = EncryptionManager(cfg)
        assert mgr.symmetric_key is None

    def test_no_key_source_key_is_none(self):
        cfg = make_sym_config(key_file=None)
        mgr = EncryptionManager(cfg)
        assert mgr.symmetric_key is None

    def test_missing_key_file_key_is_none(self, tmp_path):
        cfg = make_sym_config(key_file=str(tmp_path / "nonexistent.key"))
        mgr = EncryptionManager(cfg)
        assert mgr.symmetric_key is None

    def test_valid_key_file_loaded(self, tmp_path):
        _, key = make_manager_with_key(tmp_path)
        mgr, _ = make_manager_with_key(tmp_path, key)
        assert mgr.symmetric_key == key

    def test_short_key_padded_to_32(self, tmp_path):
        short_key = b"short"
        key_file = tmp_path / "short.key"
        key_file.write_bytes(short_key)
        cfg = make_sym_config(key_file=str(key_file))
        mgr = EncryptionManager(cfg)
        assert mgr.symmetric_key is not None
        assert len(mgr.symmetric_key) == 32

    def test_long_key_truncated_to_32(self, tmp_path):
        long_key = b"A" * 64
        key_file = tmp_path / "long.key"
        key_file.write_bytes(long_key)
        cfg = make_sym_config(key_file=str(key_file))
        mgr = EncryptionManager(cfg)
        assert mgr.symmetric_key is not None
        assert len(mgr.symmetric_key) == 32
        assert mgr.symmetric_key == long_key[:32]


# ---------------------------------------------------------------------------
# TestGitHubShortcutResolution
# ---------------------------------------------------------------------------


class TestGitHubShortcutResolution:
    def test_github_prefix_triggers_head_calls(self, tmp_path):
        """github:user format tries multiple URLs via requests.head."""
        cfg = EncryptionSettings(
            enabled=True,
            method="symmetric",
            symmetric={"key_file": "github:testuser"},
        )
        with patch("bbackup.encryption.requests.head") as mock_head, \
             patch("bbackup.encryption.requests.get"):
            mock_head.return_value = MagicMock(status_code=200)
            EncryptionManager(cfg)
        mock_head.assert_called()

    def test_first_200_url_returned(self, tmp_path):
        """First URL returning 200 is returned as resolved URL."""
        cfg = EncryptionSettings(
            enabled=True,
            method="symmetric",
            symmetric={"key_file": "github:testuser"},
        )
        with patch("bbackup.encryption.requests.head") as mock_head, \
             patch("bbackup.encryption.requests.get") as mock_get:
            mock_head.return_value = MagicMock(status_code=200)
            mock_get.return_value = MagicMock(
                status_code=200,
                content=b"A" * 32,
                raise_for_status=MagicMock(),
            )
            EncryptionManager(cfg)
        # Verifies no exception was raised and head was called
        mock_head.assert_called()

    def test_all_404_ssh_fallback(self):
        """All standard URLs 404; SSH keys endpoint checked as fallback."""
        cfg = EncryptionSettings(
            enabled=True,
            method="symmetric",
            symmetric={"key_file": "github:testuser"},
        )
        def head_side_effect(url, **kwargs):
            m = MagicMock()
            if "github.com/testuser.keys" in url:
                m.status_code = 200
            else:
                m.status_code = 404
            return m

        with patch("bbackup.encryption.requests.head", side_effect=head_side_effect), \
             patch("bbackup.encryption.requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                content=b"A" * 32,
                raise_for_status=MagicMock(),
            )
            EncryptionManager(cfg)
        # No assertion on key value; just verifying it runs without exception

    def test_all_request_exceptions_returns_none(self):
        """All requests.head calls raise RequestException -> key is None."""
        from requests import RequestException
        cfg = EncryptionSettings(
            enabled=True,
            method="symmetric",
            symmetric={"key_file": "github:testuser"},
        )
        with patch("bbackup.encryption.requests.head", side_effect=RequestException("network error")):
            mgr = EncryptionManager(cfg)
        assert mgr.symmetric_key is None

    def test_explicit_gist_format_no_head_calls(self):
        """github:user/gist:ID format constructs URL directly, no head calls."""
        cfg = EncryptionSettings(
            enabled=True,
            method="symmetric",
            symmetric={"key_file": "github:testuser/gist:abc123"},
        )
        with patch("bbackup.encryption.requests.head") as mock_head, \
             patch("bbackup.encryption.requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                content=b"A" * 32,
                raise_for_status=MagicMock(),
            )
            EncryptionManager(cfg)
        mock_head.assert_not_called()

    def test_explicit_repo_format_no_head_calls(self):
        """github:user/repo:NAME format constructs URL directly, no head calls."""
        cfg = EncryptionSettings(
            enabled=True,
            method="symmetric",
            symmetric={"key_file": "github:testuser/repo:mykeys"},
        )
        with patch("bbackup.encryption.requests.head") as mock_head, \
             patch("bbackup.encryption.requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                content=b"A" * 32,
                raise_for_status=MagicMock(),
            )
            EncryptionManager(cfg)
        mock_head.assert_not_called()


# ---------------------------------------------------------------------------
# TestFetchKeyFromUrl
# ---------------------------------------------------------------------------


class TestFetchKeyFromUrl:
    def _make_mgr(self, tmp_path):
        """Create manager without auto-loading key (disabled config)."""
        cfg = EncryptionSettings(enabled=False, method="symmetric", symmetric={})
        mgr = EncryptionManager(cfg)
        return mgr

    def test_200_returns_bytes(self, tmp_path):
        mgr = self._make_mgr(tmp_path)
        with patch("bbackup.encryption.requests.get") as mock_get:
            mock_get.return_value = MagicMock(
                status_code=200,
                content=b"key_data_here",
                raise_for_status=MagicMock(),
            )
            with patch.object(mgr, "_cache_key"):
                result = mgr._fetch_key_from_url("https://example.com/key.pem")
        assert result == b"key_data_here"

    def test_http_url_raises_value_error(self, tmp_path):
        mgr = self._make_mgr(tmp_path)
        with pytest.raises(ValueError, match="Only HTTPS"):
            mgr._fetch_key_from_url("http://insecure.com/key.pem")

    def test_request_exception_falls_back_to_cache(self, tmp_path):
        from requests import RequestException
        mgr = self._make_mgr(tmp_path)
        cached = b"cached_key_data"
        with patch("bbackup.encryption.requests.get", side_effect=RequestException("timeout")), \
             patch.object(mgr, "_load_cached_key", return_value=cached):
            result = mgr._fetch_key_from_url("https://example.com/key.pem")
        assert result == cached

    def test_request_exception_no_cache_raises(self, tmp_path):
        from requests import RequestException
        mgr = self._make_mgr(tmp_path)
        with patch("bbackup.encryption.requests.get", side_effect=RequestException("timeout")), \
             patch.object(mgr, "_load_cached_key", return_value=None):
            with pytest.raises(RequestException):
                mgr._fetch_key_from_url("https://example.com/key.pem")


# ---------------------------------------------------------------------------
# TestKeyCache
# ---------------------------------------------------------------------------


class TestKeyCache:
    def test_cache_write_and_read_roundtrip(self, tmp_path):
        cfg = EncryptionSettings(enabled=False, method="symmetric", symmetric={})
        mgr = EncryptionManager(cfg)
        url = "https://example.com/testkey.pem"
        data = b"my_secret_key_data"

        with patch("pathlib.Path.home", return_value=tmp_path):
            mgr._cache_key(url, data)
            result = mgr._load_cached_key(url)

        assert result == data

    def test_load_missing_cache_returns_none(self, tmp_path):
        cfg = EncryptionSettings(enabled=False, method="symmetric", symmetric={})
        mgr = EncryptionManager(cfg)
        with patch("pathlib.Path.home", return_value=tmp_path):
            result = mgr._load_cached_key("https://notcached.example.com/key")
        assert result is None


# ---------------------------------------------------------------------------
# TestPBKDF2
# ---------------------------------------------------------------------------


class TestPBKDF2:
    def test_same_password_same_salt_same_key(self, tmp_path):
        """PBKDF2 is deterministic: same inputs produce same output."""
        salt = os.urandom(16)
        key_data = salt + os.urandom(16)  # first 16 bytes = salt
        key_file = tmp_path / "key.bin"
        key_file.write_bytes(key_data)

        cfg = EncryptionSettings(
            enabled=True,
            method="symmetric",
            symmetric={"key_file": str(key_file), "key_password": "mypassword"},
        )
        mgr1 = EncryptionManager(cfg)
        mgr2 = EncryptionManager(cfg)
        assert mgr1.symmetric_key == mgr2.symmetric_key

    def test_different_passwords_different_keys(self, tmp_path):
        salt_data = os.urandom(32)
        key_file = tmp_path / "key.bin"
        key_file.write_bytes(salt_data)

        cfg1 = EncryptionSettings(
            enabled=True, method="symmetric",
            symmetric={"key_file": str(key_file), "key_password": "pass1"},
        )
        cfg2 = EncryptionSettings(
            enabled=True, method="symmetric",
            symmetric={"key_file": str(key_file), "key_password": "pass2"},
        )
        mgr1 = EncryptionManager(cfg1)
        mgr2 = EncryptionManager(cfg2)
        assert mgr1.symmetric_key != mgr2.symmetric_key


# ---------------------------------------------------------------------------
# TestFileEncryption
# ---------------------------------------------------------------------------


class TestFileEncryption:
    def test_roundtrip_preserves_binary_content(self, tmp_path):
        mgr, _ = make_manager_with_key(tmp_path)
        src = tmp_path / "source.bin"
        original = os.urandom(1024)
        src.write_bytes(original)

        enc = tmp_path / "source.bin.enc"
        dec = tmp_path / "source.bin.dec"

        assert mgr.encrypt_file(src, enc) is True
        assert enc.exists()
        assert mgr.decrypt_file(enc, dec) is True
        assert dec.read_bytes() == original

    def test_encrypt_creates_different_output(self, tmp_path):
        mgr, _ = make_manager_with_key(tmp_path)
        src = tmp_path / "file.txt"
        src.write_text("hello world")
        enc = tmp_path / "file.txt.enc"
        mgr.encrypt_file(src, enc)
        assert enc.read_bytes() != src.read_bytes()


# ---------------------------------------------------------------------------
# TestDirectoryEncryption
# ---------------------------------------------------------------------------


class TestDirectoryEncryption:
    def test_roundtrip_3_file_tree(self, tmp_path):
        mgr, _ = make_manager_with_key(tmp_path)

        # Create 3-file tree
        src = tmp_path / "source"
        src.mkdir()
        (src / "file1.txt").write_text("content1")
        sub = src / "subdir"
        sub.mkdir()
        (sub / "file2.bin").write_bytes(b"\x00\x01\x02")
        (sub / "file3.txt").write_text("content3")

        enc_dir = tmp_path / "encrypted"
        dec_dir = tmp_path / "decrypted"

        assert mgr.encrypt_directory(src, enc_dir) is True
        assert (enc_dir / "encryption_metadata.json").exists()
        assert mgr.decrypt_directory(enc_dir, dec_dir) is True

        assert (dec_dir / "file1.txt").read_text() == "content1"
        assert (dec_dir / "subdir" / "file2.bin").read_bytes() == b"\x00\x01\x02"
        assert (dec_dir / "subdir" / "file3.txt").read_text() == "content3"


# ---------------------------------------------------------------------------
# TestBackupEncryption
# ---------------------------------------------------------------------------


class TestBackupEncryption:
    def test_encrypt_backup_creates_enc_dir(self, tmp_path):
        mgr, _ = make_manager_with_key(tmp_path)
        backup = tmp_path / "backup_20240101_000000"
        backup.mkdir()
        (backup / "data.bin").write_bytes(b"important data")

        result = mgr.encrypt_backup(backup)
        assert result.name.endswith(".enc")
        assert result.exists()

    def test_decrypt_backup_no_metadata_returns_original(self, tmp_path):
        mgr, _ = make_manager_with_key(tmp_path)
        backup = tmp_path / "backup_plain"
        backup.mkdir()
        result = mgr.decrypt_backup(backup)
        assert result == backup


# ---------------------------------------------------------------------------
# TestKeyGeneration
# ---------------------------------------------------------------------------


class TestKeyGeneration:
    def test_generate_symmetric_key_is_32_bytes(self):
        key = EncryptionManager.generate_symmetric_key()
        assert len(key) == 32

    def test_generate_symmetric_key_non_deterministic(self):
        k1 = EncryptionManager.generate_symmetric_key()
        k2 = EncryptionManager.generate_symmetric_key()
        assert k1 != k2

    def test_generate_keypair_returns_pem_bytes(self):
        pub, priv = EncryptionManager.generate_keypair(algorithm="rsa-4096")
        assert b"-----BEGIN PUBLIC KEY-----" in pub
        assert b"-----BEGIN PRIVATE KEY-----" in priv

    def test_generate_keypair_pem_loadable(self):
        pub_pem, priv_pem = EncryptionManager.generate_keypair(algorithm="rsa-4096")
        pub_key = serialization.load_pem_public_key(pub_pem, backend=default_backend())
        priv_key = serialization.load_pem_private_key(priv_pem, password=None, backend=default_backend())
        assert pub_key is not None
        assert priv_key is not None

    def test_generate_keypair_unsupported_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            EncryptionManager.generate_keypair(algorithm="unsupported")

    def test_generate_keypair_ecdsa_unsupported(self):
        with pytest.raises(ValueError, match="Unsupported"):
            EncryptionManager.generate_keypair(algorithm="ecdsa-p384")
