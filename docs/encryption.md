# Encryption

> How bbackup encrypts backups at rest, including key generation, configuration, and multi-server deployment.

---

## How it works

Encryption happens after all backup files are written and before they are uploaded to any remote. Each file gets its own random IV so identical files produce different ciphertext. Decryption runs automatically on restore when the config includes a private key.

Two modes are available:

**Symmetric (AES-256-GCM):** One key does both encryption and decryption. Simpler to set up. Good for single-server setups where the same machine backs up and restores.

**Asymmetric (RSA-4096):** A public key encrypts, a private key decrypts. The public key can be shared or posted publicly. The private key stays on the restore machine only. This is the right choice when backup servers and restore servers are different machines, or when you want to separate the ability to create backups from the ability to read them.

When encryption succeeds, bbackup removes the plaintext staging directory and keeps the encrypted directory or encrypted solid archive as the local artifact. If encryption is enabled but fails, backup upload is aborted rather than falling back to plaintext.

---

## Quick setup

### Symmetric

```bash
bbackup init-encryption --method symmetric
```

Creates `~/.config/bbackup/encryption.key`. Add to your config:

```yaml
encryption:
  enabled: true
  method: symmetric
  symmetric:
    key_file: ~/.config/bbackup/encryption.key
```

### Asymmetric

```bash
bbackup init-encryption --method asymmetric --algorithm rsa-4096
```

Creates:
- `~/.config/bbackup/backup_public.pem` (safe to share)
- `~/.config/bbackup/backup_private.pem` (keep this secret)

Config:

```yaml
encryption:
  enabled: true
  method: asymmetric
  asymmetric:
    public_key: ~/.config/bbackup/backup_public.pem
    private_key: ~/.config/bbackup/backup_private.pem
    algorithm: rsa-4096
```

---

## Hosting keys on GitHub

Copying key files to every backup server manually is annoying. The public key can be hosted on GitHub and referenced by URL or shortcut instead.

### Upload the public key to a Gist

1. Go to [gist.github.com](https://gist.github.com)
2. Paste the contents of `backup_public.pem`
3. Create the gist (can be secret)
4. Click "Raw" to get the URL

### Reference it in config

Full Gist URL:

```yaml
encryption:
  asymmetric:
    public_key: https://gist.githubusercontent.com/YOUR_USERNAME/YOUR_GIST_ID/raw/backup_public.pem
```

GitHub shortcuts (bbackup resolves these automatically):

```yaml
# Explicit gist ID
public_key: github:YOUR_USERNAME/gist:YOUR_GIST_ID

# Explicit repo
public_key: github:YOUR_USERNAME/repo:backup-keys

# Username only - auto-discovery (tries standard locations)
public_key: github:YOUR_USERNAME
# or the shorter alias:
public_key: gh:YOUR_USERNAME
```

When you use the username-only form, bbackup tries these four URLs in order:

```
https://gist.githubusercontent.com/USERNAME/bbackup-keys/raw/backup_public.pem
https://gist.githubusercontent.com/USERNAME/backup-keys/raw/backup_public.pem
https://raw.githubusercontent.com/USERNAME/bbackup-keys/main/backup_public.pem
https://raw.githubusercontent.com/USERNAME/backup-keys/main/backup_public.pem
```

So naming your Gist `bbackup-keys` or `backup-keys` and your key file `backup_public.pem` is all you need. Raw repo URL also works:

```
https://raw.githubusercontent.com/YOUR_USERNAME/REPO/main/backup_public.pem
```

When a URL is used, bbackup downloads and caches the key at `~/.cache/bbackup/keys/` with permissions set to 600. If the URL is unreachable on a later run, the cached copy is used.

---

## Multi-server deployment

### Backup servers encrypt, restore server decrypts

This is the most common production setup.

**All backup servers** need only the public key:

```yaml
encryption:
  enabled: true
  method: asymmetric
  asymmetric:
    public_key: https://gist.githubusercontent.com/YOUR_USERNAME/YOUR_GIST_ID/raw/backup_public.pem
```

**Restore server** also needs the private key:

```yaml
encryption:
  enabled: true
  method: asymmetric
  asymmetric:
    public_key: https://gist.githubusercontent.com/YOUR_USERNAME/YOUR_GIST_ID/raw/backup_public.pem
    private_key: ~/.config/bbackup/backup_private.pem
```

The private key never leaves the restore server. Even if a backup server is compromised, the encrypted data cannot be read without it.

---

## Key management

### File permissions

| File | Permissions |
|---|---|
| Private key | `600` (owner only) |
| Symmetric key | `600` (owner only) |
| Public key | `644` (readable) |

bbackup sets these automatically when generating keys.

### Password-protecting key files

```yaml
encryption:
  asymmetric:
    private_key: ~/.config/bbackup/backup_private.pem
    private_key_password: "your-passphrase"
```

### Key rotation

1. Generate a new keypair: `bbackup init-encryption --method asymmetric`
2. Upload the new public key to GitHub
3. Update the public key URL in config on all servers
4. Distribute the new private key to restore servers
5. Keep the old private key around to decrypt existing backups if needed

---

## Security notes

- Never upload private keys to GitHub or any URL. Private keys must stay as local files.
- bbackup requires HTTPS for any key URL. HTTP is rejected.
- The private key is only needed on machines that perform restores.
- Symmetric keys give every machine that has them the ability to decrypt backups. Use asymmetric mode if that is a concern.

---

## Troubleshooting

**"Failed to fetch key from URL"**

Check network access and confirm the URL is reachable. If the key was cached previously, bbackup will fall back to the cached copy. Clear the cache with `rm -rf ~/.cache/bbackup/keys/` and retry.

**"No encryption key available"**

The key path in config does not exist or is not readable. Check that the file is at the expected location and has the right permissions.

**"Decryption failed"**

Either the wrong private key is configured, or the encrypted file is corrupted. Verify the private key matches the public key that was used during backup.

---

Back to [README.md](../README.md).

<!-- project-footer:start -->

<br><br>

<p align="center">
Slavic Kozyuk<br>
&copy; 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> &mdash; <a href="https://github.com/CruxExperts/best-backup/blob/main/LICENSE">MIT License</a>
</p>

<!-- project-footer:end -->
