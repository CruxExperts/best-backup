"""
Google Drive OAuth setup helper for rclone-backed bbackup remotes.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import timezone
from pathlib import Path
from typing import Any


INSTALL_HINT = (
    "Google Drive OAuth support is optional. Install it with "
    "`uv sync --extra gdrive-auth` or `pip install 'bbackup[gdrive-auth]'`."
)

REDACTION = "<redacted>"
DRIVE_SCOPE_URL = "https://www.googleapis.com/auth/drive"
DEFAULT_HOST = "127.0.0.1"


class GDriveAuthError(Exception):
    """Base class for expected auth-gdrive failures."""

    exit_code = 1


class OptionalDependencyMissing(GDriveAuthError):
    """Raised when google-auth-oauthlib is not installed."""

    exit_code = 1


class RcloneError(GDriveAuthError):
    """Raised when rclone is missing or fails."""

    exit_code = 3


@dataclass
class ClientSecrets:
    path: Path
    client_id: str
    client_secret: str


SENSITIVE_KEYS = {
    "access_token",
    "refresh_token",
    "client_secret",
    "token",
}


def redact(value: Any, secrets: list[str] | None = None) -> Any:
    """Recursively redact tokens and known secret values from data or text."""
    secrets = [s for s in (secrets or []) if s]
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in SENSITIVE_KEYS:
                redacted[key] = REDACTION
            else:
                redacted[key] = redact(item, secrets)
        return redacted
    if isinstance(value, list):
        return [redact(item, secrets) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item, secrets) for item in value)
    if isinstance(value, str):
        text = value
        for secret in secrets:
            text = text.replace(secret, REDACTION)
        return text
    return value


def load_client_secrets(path: str | Path) -> ClientSecrets:
    """Validate and load an installed-app Google OAuth client secrets file."""
    secrets_path = Path(path).expanduser()
    try:
        raw = json.loads(secrets_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GDriveAuthError(f"Client secrets file not found: {secrets_path}") from exc
    except json.JSONDecodeError as exc:
        raise GDriveAuthError(f"Client secrets file is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise GDriveAuthError(f"Could not read client secrets file: {exc}") from exc
    if not isinstance(raw, dict):
        raise GDriveAuthError("Client secrets file must contain a top-level JSON object.")


    if "web" in raw and "installed" not in raw:
        raise GDriveAuthError(
            "Client secrets file contains a web OAuth client. Create a Desktop app OAuth client instead."
        )
    installed = raw.get("installed")
    if not isinstance(installed, dict):
        raise GDriveAuthError(
            "Client secrets file must contain an `installed` desktop OAuth client."
        )

    required = ["client_id", "client_secret", "auth_uri", "token_uri"]
    invalid = [
        key
        for key in required
        if not isinstance(installed.get(key), str) or not installed[key].strip()
    ]
    if invalid:
        raise GDriveAuthError(
            "Installed OAuth client requires non-empty string field(s): " + ", ".join(invalid)
        )

    return ClientSecrets(
        path=secrets_path,
        client_id=str(installed["client_id"]),
        client_secret=str(installed["client_secret"]),
    )


def oauth_scope(scope: str) -> str:
    """Return the OAuth scope URL for an rclone Drive scope name."""
    if scope == "drive":
        return DRIVE_SCOPE_URL
    if scope.startswith("https://www.googleapis.com/auth/"):
        return scope
    return f"https://www.googleapis.com/auth/{scope}"


def credentials_to_rclone_token(credentials: Any) -> str:
    """Convert google-auth credentials into the token JSON shape rclone accepts."""
    refresh_token = getattr(credentials, "refresh_token", None)
    if not refresh_token:
        raise GDriveAuthError(
            "Google did not return a refresh token. Revoke the app grant, then re-run auth-gdrive."
        )

    expiry = getattr(credentials, "expiry", None)
    expiry_text = None
    if expiry is not None:
        if getattr(expiry, "tzinfo", None) is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        expiry_text = expiry.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    token_type = getattr(credentials, "token_type", None) or "Bearer"
    token = {
        "access_token": getattr(credentials, "token", None),
        "token_type": token_type,
        "refresh_token": refresh_token,
        "expiry": expiry_text,
    }
    return json.dumps(token, separators=(",", ":"))


def token_component_secrets(token_json: str) -> list[str]:
    """Return individual token values that should be redacted from diagnostics."""
    try:
        token = json.loads(token_json)
    except json.JSONDecodeError:
        return []
    return [
        str(value)
        for key, value in token.items()
        if key in {"access_token", "refresh_token"} and value
    ]


def _load_installed_app_flow():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise OptionalDependencyMissing(INSTALL_HINT) from exc
    return InstalledAppFlow


def run_oauth_flow(
    *,
    client_secrets_path: Path,
    scope: str,
    port: int,
    timeout: int,
    open_browser: bool,
    suppress_prompt: bool = False,
):
    """Run the supported desktop loopback OAuth flow."""
    InstalledAppFlow = _load_installed_app_flow()
    flow = InstalledAppFlow.from_client_secrets_file(
        str(client_secrets_path),
        scopes=[oauth_scope(scope)],
        autogenerate_code_verifier=True,
    )
    kwargs: dict[str, Any] = {}
    if suppress_prompt:
        kwargs["authorization_prompt_message"] = ""
    return flow.run_local_server(
        host=DEFAULT_HOST,
        port=port,
        open_browser=open_browser,
        timeout_seconds=timeout,
        **kwargs,
    )


def _rclone_remote_config(remote: str) -> dict[str, str] | None:
    result = subprocess.run(
        ["rclone", "config", "dump"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RcloneError(f"Could not read rclone config (exit {result.returncode}).")
    try:
        config = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RcloneError(f"Could not parse rclone config: {exc}") from exc
    if not isinstance(config, dict):
        raise RcloneError("Could not parse rclone config: expected a JSON object.")
    remote_config = config.get(remote)
    if not isinstance(remote_config, dict):
        return None
    return {str(key): str(value) for key, value in remote_config.items()}


def _preflight_rclone_config(remote: str, force: bool) -> str:
    if not shutil.which("rclone"):
        raise RcloneError("rclone is not installed or not on PATH.")

    existing_config = _rclone_remote_config(remote)
    if existing_config is None:
        return "create"
    if existing_config.get("type") != "drive":
        raise GDriveAuthError(
            f"rclone remote `{remote}` already exists and is type "
            f"`{existing_config.get('type', 'unknown')}`, not `drive`."
        )
    if not force:
        raise GDriveAuthError(
            f"rclone remote `{remote}` already exists. Re-run with --force to update it."
        )
    return "update"

def _wait_for_rc(socket_path: Path, process: subprocess.Popen[str], timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RcloneError("rclone rc server exited before it was ready.")
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(0.2)
                client.connect(str(socket_path))
                return
        except OSError:
            pass
        time.sleep(0.05)
    raise RcloneError("Timed out waiting for rclone rc server.")


def _rc_post(socket_path: Path, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = (
        f"POST /{method} HTTP/1.1\r\n"
        "Host: localhost\r\n"
        "Content-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("ascii") + body

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(10)
        client.connect(str(socket_path))
        client.sendall(request)
        chunks = []
        while True:
            chunk = client.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)

    response = b"".join(chunks)
    header, _, response_body = response.partition(b"\r\n\r\n")
    status_line = header.splitlines()[0].decode("ascii", errors="replace") if header else ""
    if " 200 " not in status_line:
        raise RcloneError(response_body.decode("utf-8", errors="replace") or status_line)
    if not response_body:
        return {}
    return json.loads(response_body.decode("utf-8"))


def _call_rclone_rc(method: str, payload: dict[str, Any], secrets: list[str]) -> dict[str, Any]:
    if not hasattr(socket, "AF_UNIX"):
        raise RcloneError("rclone configuration requires Unix-domain socket support.")

    with tempfile.TemporaryDirectory(prefix="bbackup-rclone-rc-") as rc_dir:
        os.chmod(rc_dir, 0o700)
        socket_path = Path(rc_dir) / "rc.sock"
        cmd = [
            "rclone",
            "rcd",
            "--rc-addr",
            str(socket_path),
            "--rc-no-auth",
            "--rc-web-gui=false",
        ]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            _wait_for_rc(socket_path, process)
            return _rc_post(socket_path, method, payload)
        except Exception as exc:
            if process.poll() is not None and process.stderr is not None:
                stderr = process.stderr.read().strip()
                if stderr:
                    raise RcloneError(str(redact(stderr, secrets))) from exc
            raise RcloneError(str(redact(str(exc), secrets))) from exc
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


def _rclone_config_response(response: dict[str, Any], secrets: list[str]) -> tuple[str, str]:
    """Inspect an RC config response and return its next state and result."""
    if not isinstance(response, dict):
        raise RcloneError("rclone config returned an invalid response.")

    error = response.get("Error", response.get("error"))
    if error:
        details = str(redact(error, secrets))
        raise RcloneError(f"rclone config failed: {details}")

    option = response.get("Option", response.get("option"))
    if option:
        details = json.dumps(redact(response, secrets), sort_keys=True)
        raise RcloneError(
            "rclone requested additional configuration input; "
            f"non-interactive setup cannot continue: {details}"
        )

    state = response.get("State", response.get("state")) or ""
    result = response.get("Result", response.get("result")) or ""
    if not isinstance(state, str) or not isinstance(result, str):
        raise RcloneError("rclone config returned an invalid continuation response.")
    return state, result


def _run_rclone_config(
    *,
    remote: str,
    client_id: str,
    client_secret: str,
    scope: str,
    token_json: str,
    action: str,
) -> dict[str, Any]:

    parameters = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": scope,
        "token": token_json,
        "config_refresh_token": "false",
        "config_change_team_drive": "false",
    }
    if action not in {"create", "update"}:
        raise RcloneError(f"Unsupported rclone configuration action: {action}")
    secrets = [client_secret, token_json] + token_component_secrets(token_json)
    if action == "update":
        method = "config/update"
        payload = {
            "name": remote,
            "parameters": parameters,
            "opt": {"obscure": True, "nonInteractive": True, "noOutput": True},
        }
    else:
        action = "create"
        method = "config/create"
        payload = {
            "name": remote,
            "type": "drive",
            "parameters": parameters,
            "opt": {"obscure": True, "nonInteractive": True, "noOutput": True},
        }

    response = _call_rclone_rc(method, payload, secrets)
    for step in range(33):
        state, result = _rclone_config_response(response, secrets)
        if not state:
            break
        if step == 32:
            raise RcloneError("rclone config did not complete within 32 continuation steps.")
        payload = {
            **payload,
            "opt": {
                **payload["opt"],
                "continue": True,
                "state": state,
                "result": result,
            },
        }
        response = _call_rclone_rc(method, payload, secrets)

    return {
        "remote": remote,
        "action": action,
        "rclone_command": [
            "rclone",
            "rcd",
            "--rc-addr",
            "<private-temporary-unix-socket>",
            "--rc-no-auth",
            "--rc-web-gui=false",
        ],
        "rc_auth": {"transport": "mode-0700-unix-socket"},
        "rc_method": method,
    }


def auth_gdrive(
    *,
    client_secrets: str | Path,
    remote: str = "bbackup-gdrive",
    scope: str = "drive",
    port: int = 53682,
    timeout: int = 300,
    open_browser: bool = True,
    suppress_oauth_prompt: bool = False,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Validate, authorize, and configure an rclone Google Drive remote."""
    loaded = load_client_secrets(client_secrets)
    if dry_run:
        action = "update" if force else "create-or-error-if-existing"
        return {
            "remote": remote,
            "scope": scope,
            "client_id": loaded.client_id,
            "client_secrets_path": str(loaded.path),
            "dry_run": True,
            "oauth": {
                "host": DEFAULT_HOST,
                "port": port,
                "timeout_seconds": timeout,
                "open_browser": open_browser,
                "scope": oauth_scope(scope),
                "will_run": False,
            },
            "rclone": {
                "will_write": False,
                "planned_action": action,
                "config_refresh_token": "false",
            },
        }

    rclone_action = _preflight_rclone_config(remote, force)

    try:
        credentials = run_oauth_flow(
            client_secrets_path=loaded.path,
            scope=scope,
            port=port,
            timeout=timeout,
            open_browser=open_browser,
            suppress_prompt=suppress_oauth_prompt,
        )
    except GDriveAuthError:
        raise
    except Exception as exc:
        raise GDriveAuthError(str(redact(str(exc), [loaded.client_secret]))) from exc

    token_json = credentials_to_rclone_token(credentials)
    try:
        rclone_result = _run_rclone_config(
            remote=remote,
            client_id=loaded.client_id,
            client_secret=loaded.client_secret,
            scope=scope,
            token_json=token_json,
            action=rclone_action,
        )
    except GDriveAuthError:
        raise
    except Exception as exc:
        raise RcloneError(str(redact(str(exc), [loaded.client_secret, token_json]))) from exc

    return {
        "remote": remote,
        "scope": scope,
        "client_id": loaded.client_id,
        "client_secrets_path": str(loaded.path),
        "dry_run": False,
        "oauth": {
            "host": DEFAULT_HOST,
            "port": port,
            "timeout_seconds": timeout,
            "open_browser": open_browser,
            "scope": oauth_scope(scope),
            "refresh_token": REDACTION,
        },
        "rclone": rclone_result,
    }
