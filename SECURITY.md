# Security policy

> How to report vulnerabilities in bbackup.

---

## Supported versions

Security fixes are applied to the latest release only. Older versions are not backported.

| Version | Supported |
|---|---|
| Latest release | ✅ |
| Older releases | ❌ |

---

## Reporting a vulnerability

Please do not open a public GitHub issue for security vulnerabilities.

Use GitHub's private vulnerability reporting instead:

1. Go to the [Security tab](https://github.com/CruxExperts/best-backup/security) of this repository.
2. Click "Report a vulnerability."
3. Describe the issue, steps to reproduce, and potential impact.

You can expect an acknowledgement within 5 business days. If the report is confirmed, a fix will be prepared and a new release cut as soon as reasonably possible. You will be credited in the release notes unless you prefer otherwise.

---

## Scope

This policy covers the bbackup source code in this repository. It does not cover third-party tools that bbackup optionally depends on (Docker, rsync, rclone, paramiko), or the host operating system.

---

## General guidance

- Never commit encryption keys, API tokens, or credentials to this repository.
- The `.gitignore` already excludes `*.pem`, `*.key`, and `.env` files.
- If you store keys at the paths bbackup defaults to (`~/.config/bbackup/`), ensure directory permissions are `700` and file permissions are `600`.

---

Back to [README.md](README.md).

<!-- project-footer:start -->

<br><br>

<p align="center">
Slavic Kozyuk<br>
&copy; 2026 <a href="https://www.cruxexperts.com/">Crux Experts LLC</a> &mdash; <a href="https://github.com/CruxExperts/best-backup/blob/main/LICENSE">MIT License</a>
</p>

<!-- project-footer:end -->
