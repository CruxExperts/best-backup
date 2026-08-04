"""
Tests for bbman auth-gdrive and its rclone OAuth helper.
"""

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from bbackup.bbman import cli as bbman_cli
from bbackup.cli_utils import EXIT_SUCCESS, EXIT_USER_ERROR
from bbackup.management import gdrive_auth


def write_client_secrets(tmp_path, *, section="installed", client_secret="super-secret"):
    path = tmp_path / "client_secret.json"
    path.write_text(json.dumps({
        section: {
            "client_id": "client-id.apps.googleusercontent.com",
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }))
    return path


def fake_credentials(*, refresh_token="refresh-secret"):
    return SimpleNamespace(
        token="access-secret",
        token_type="Bearer",
        refresh_token=refresh_token,
        expiry=datetime(2026, 7, 9, 13, 30, tzinfo=timezone.utc),
    )


def test_missing_optional_dependency_returns_install_hint(tmp_path):
    secrets = write_client_secrets(tmp_path)
    with patch(
        "bbackup.management.gdrive_auth._load_installed_app_flow",
        side_effect=gdrive_auth.OptionalDependencyMissing(gdrive_auth.INSTALL_HINT),
    ):
        result = CliRunner().invoke(
            bbman_cli,
            ["auth-gdrive", "--client-secrets", str(secrets), "--output", "json"],
        )

    assert result.exit_code == EXIT_USER_ERROR
    data = json.loads(result.output)
    assert data["success"] is False
    assert "uv sync --extra gdrive-auth" in data["errors"][0]


def test_run_oauth_flow_can_suppress_prompt(tmp_path):
    secrets = write_client_secrets(tmp_path)
    calls = []

    class FakeFlow:
        @classmethod
        def from_client_secrets_file(cls, path, scopes, autogenerate_code_verifier):
            assert path == str(secrets)
            assert scopes == [gdrive_auth.DRIVE_SCOPE_URL]
            assert autogenerate_code_verifier is True
            return cls()

        def run_local_server(self, **kwargs):
            calls.append(kwargs)
            return fake_credentials()

    with patch("bbackup.management.gdrive_auth._load_installed_app_flow", return_value=FakeFlow):
        gdrive_auth.run_oauth_flow(
            client_secrets_path=secrets,
            scope="drive",
            port=53682,
            timeout=300,
            open_browser=False,
            suppress_prompt=True,
        )

    assert calls[0]["authorization_prompt_message"] == ""


def test_missing_client_secrets_fails_safely(tmp_path):
    with pytest.raises(gdrive_auth.GDriveAuthError) as exc:
        gdrive_auth.load_client_secrets(tmp_path / "missing.json")
    assert "not found" in str(exc.value)


def test_web_oauth_client_is_rejected(tmp_path):
    secrets = write_client_secrets(tmp_path, section="web")
    try:
        gdrive_auth.load_client_secrets(secrets)
    except gdrive_auth.GDriveAuthError as exc:
        assert "web OAuth client" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("web client should be rejected")


@pytest.mark.parametrize("payload", [[], None, "client"])
def test_non_object_client_secrets_are_rejected_as_user_errors(tmp_path, payload):
    secrets = tmp_path / "client_secret.json"
    secrets.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(gdrive_auth.GDriveAuthError) as exc:
        gdrive_auth.load_client_secrets(secrets)

    assert "top-level JSON object" in str(exc.value)


def test_installed_oauth_client_is_accepted(tmp_path):
    secrets = write_client_secrets(tmp_path)
    loaded = gdrive_auth.load_client_secrets(secrets)
    assert loaded.client_id == "client-id.apps.googleusercontent.com"
    assert loaded.client_secret == "super-secret"


def test_installed_oauth_fields_must_be_non_empty_strings(tmp_path):
    secrets = write_client_secrets(tmp_path)
    payload = json.loads(secrets.read_text(encoding="utf-8"))
    payload["installed"]["client_secret"] = 123
    secrets.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(gdrive_auth.GDriveAuthError) as exc:
        gdrive_auth.load_client_secrets(secrets)

    assert "non-empty string field(s): client_secret" in str(exc.value)


def test_credentials_to_rclone_token_mapping():
    token_json = gdrive_auth.credentials_to_rclone_token(fake_credentials())
    token = json.loads(token_json)
    assert token == {
        "access_token": "access-secret",
        "token_type": "Bearer",
        "refresh_token": "refresh-secret",
        "expiry": "2026-07-09T13:30:00Z",
    }


def test_token_component_secrets_extracts_token_values():
    token_json = gdrive_auth.credentials_to_rclone_token(fake_credentials())
    assert gdrive_auth.token_component_secrets(token_json) == [
        "access-secret",
        "refresh-secret",
    ]


def test_missing_refresh_token_fails():
    try:
        gdrive_auth.credentials_to_rclone_token(fake_credentials(refresh_token=None))
    except gdrive_auth.GDriveAuthError as exc:
        assert "refresh token" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("missing refresh token should fail")


def test_redaction_removes_tokens_and_client_secret():
    value = {
        "client_secret": "super-secret",
        "nested": ["access-secret", {"refresh_token": "refresh-secret"}],
    }
    redacted = gdrive_auth.redact(value, ["access-secret", "super-secret"])
    assert "super-secret" not in json.dumps(redacted)
    assert "access-secret" not in json.dumps(redacted)
    assert "refresh-secret" not in json.dumps(redacted)
    assert json.dumps(redacted).count(gdrive_auth.REDACTION) == 3


def test_oauth_exception_redacts_client_secret(tmp_path):
    secrets = write_client_secrets(tmp_path)
    with patch(
        "bbackup.management.gdrive_auth.run_oauth_flow",
        side_effect=RuntimeError("oauth failed for super-secret"),
    ):
        with pytest.raises(gdrive_auth.GDriveAuthError) as exc:
            gdrive_auth.auth_gdrive(client_secrets=secrets)

    assert "super-secret" not in str(exc.value)
    assert gdrive_auth.REDACTION in str(exc.value)


def test_dry_run_performs_no_oauth_or_rclone_writes(tmp_path):
    secrets = write_client_secrets(tmp_path)
    with patch("bbackup.management.gdrive_auth.run_oauth_flow") as oauth, \
         patch("bbackup.management.gdrive_auth.subprocess.run") as run:
        result = gdrive_auth.auth_gdrive(client_secrets=secrets, dry_run=True)

    assert result["dry_run"] is True
    assert result["rclone"]["will_write"] is False
    oauth.assert_not_called()
    run.assert_not_called()


def test_existing_remote_requires_force_before_oauth(tmp_path):
    secrets = write_client_secrets(tmp_path)
    with patch("bbackup.management.gdrive_auth.run_oauth_flow") as oauth, \
         patch("bbackup.management.gdrive_auth.shutil.which", return_value="/usr/bin/rclone"), \
         patch("bbackup.management.gdrive_auth.subprocess.run") as run:
        run.return_value = MagicMock(returncode=0, stdout='{"bbackup-gdrive":{"type":"drive"}}', stderr="")
        try:
            gdrive_auth.auth_gdrive(client_secrets=secrets)
        except gdrive_auth.GDriveAuthError as exc:
            assert "already exists" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("existing remote should require --force")

    oauth.assert_not_called()


def test_force_rejects_existing_non_drive_remote_before_oauth(tmp_path):
    secrets = write_client_secrets(tmp_path)
    with patch("bbackup.management.gdrive_auth.run_oauth_flow") as oauth, \
         patch("bbackup.management.gdrive_auth.shutil.which", return_value="/usr/bin/rclone"), \
         patch("bbackup.management.gdrive_auth.subprocess.run") as run:
        run.return_value = MagicMock(returncode=0, stdout='{"other":{"type":"sftp"}}', stderr="")
        with pytest.raises(gdrive_auth.GDriveAuthError) as exc:
            gdrive_auth.auth_gdrive(client_secrets=secrets, remote="other", force=True)

    assert "not `drive`" in str(exc.value)
    oauth.assert_not_called()



def test_missing_rclone_fails_before_oauth(tmp_path):
    secrets = write_client_secrets(tmp_path)
    with patch("bbackup.management.gdrive_auth.run_oauth_flow") as oauth, \
         patch("bbackup.management.gdrive_auth.shutil.which", return_value=None):
        with pytest.raises(gdrive_auth.RcloneError) as exc:
            gdrive_auth.auth_gdrive(client_secrets=secrets)

    assert "not installed" in str(exc.value)
    oauth.assert_not_called()


def test_rclone_config_create_uses_rc_body_not_secret_argv(tmp_path):
    secrets = write_client_secrets(tmp_path)
    show_result = MagicMock(returncode=0, stdout="{}", stderr="")
    with patch("bbackup.management.gdrive_auth.run_oauth_flow", return_value=fake_credentials()), \
         patch("bbackup.management.gdrive_auth.shutil.which", return_value="/usr/bin/rclone"), \
         patch("bbackup.management.gdrive_auth.subprocess.run", return_value=show_result), \
         patch("bbackup.management.gdrive_auth._call_rclone_rc", return_value={}) as rc:
        result = gdrive_auth.auth_gdrive(client_secrets=secrets)

    method, payload, secrets_list = rc.call_args.args
    assert method == "config/create"
    assert payload["type"] == "drive"
    assert payload["parameters"]["token"]
    assert payload["parameters"]["client_secret"] == "super-secret"
    command_preview = " ".join(result["rclone"]["rclone_command"])
    assert "super-secret" not in command_preview
    assert "refresh-secret" not in command_preview
    assert "super-secret" in secrets_list
    assert "access-secret" in secrets_list
    assert "refresh-secret" in secrets_list


def test_rclone_config_update_with_force_sets_refresh_flag(tmp_path):
    secrets = write_client_secrets(tmp_path)
    show_result = MagicMock(returncode=0, stdout='{"bbackup-gdrive":{"type":"drive"}}', stderr="")
    with patch("bbackup.management.gdrive_auth.run_oauth_flow", return_value=fake_credentials()), \
         patch("bbackup.management.gdrive_auth.shutil.which", return_value="/usr/bin/rclone"), \
         patch("bbackup.management.gdrive_auth.subprocess.run", return_value=show_result), \
         patch("bbackup.management.gdrive_auth._call_rclone_rc", return_value={}) as rc:
        result = gdrive_auth.auth_gdrive(client_secrets=secrets, force=True)

    method, payload, _ = rc.call_args.args
    assert method == "config/update"
    assert payload["parameters"]["config_refresh_token"] == "false"
    assert result["rclone"]["action"] == "update"


def test_rc_daemon_uses_private_unix_socket_without_google_secrets_in_argv():
    process = MagicMock()
    process.poll.return_value = None
    process.wait.return_value = None
    observed = {}

    def inspect_socket_directory(socket_path, _process):
        observed["mode"] = socket_path.parent.stat().st_mode & 0o777
        observed["path"] = socket_path

    with patch("bbackup.management.gdrive_auth._wait_for_rc", side_effect=inspect_socket_directory), \
         patch("bbackup.management.gdrive_auth._rc_post", return_value={}) as rc_post, \
         patch("bbackup.management.gdrive_auth.subprocess.Popen", return_value=process) as popen:
        gdrive_auth._call_rclone_rc(
            "config/create",
            {"parameters": {"client_secret": "super-secret", "token": "refresh-secret"}},
            ["super-secret", "refresh-secret"],
        )

    argv = popen.call_args.args[0]
    assert "super-secret" not in argv
    assert "refresh-secret" not in argv
    assert argv[argv.index("--rc-addr") + 1] == str(observed["path"])
    assert "--rc-no-auth" in argv
    assert observed["mode"] == 0o700
    assert rc_post.call_args.args[0] == observed["path"]


def test_rc_post_uses_unix_socket_transport(tmp_path):
    client = MagicMock()
    client.recv.side_effect = [
        b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\n{}",
        b"",
    ]
    socket_context = MagicMock()
    socket_context.__enter__.return_value = client
    socket_path = tmp_path / "rc.sock"
    with patch("bbackup.management.gdrive_auth.socket.socket", return_value=socket_context):
        result = gdrive_auth._rc_post(socket_path, "core/version", {})

    request = client.sendall.call_args.args[0]
    assert result == {}
    client.connect.assert_called_once_with(str(socket_path))
    assert b"Host: localhost" in request
    assert b"Authorization:" not in request


def test_json_envelope_shape_for_dry_run(tmp_path):
    secrets = write_client_secrets(tmp_path)
    result = CliRunner().invoke(
        bbman_cli,
        ["auth-gdrive", "--client-secrets", str(secrets), "--dry-run", "--output", "json"],
    )

    assert result.exit_code == EXIT_SUCCESS
    data = json.loads(result.output)
    assert data["schema_version"] == "1"
    assert data["command"] == "auth-gdrive"
    assert data["success"] is True
    assert data["data"]["rclone"]["will_write"] is False


def test_json_mode_suppresses_oauth_prompt(tmp_path):
    secrets = write_client_secrets(tmp_path)
    with patch("bbackup.management.gdrive_auth.auth_gdrive") as auth:
        auth.return_value = {
            "remote": "bbackup-gdrive",
            "scope": "drive",
            "dry_run": False,
            "oauth": {},
            "rclone": {"action": "create"},
        }
        result = CliRunner().invoke(
            bbman_cli,
            ["auth-gdrive", "--client-secrets", str(secrets), "--output", "json"],
        )

    assert result.exit_code == EXIT_SUCCESS
    assert json.loads(result.output)["success"] is True
    assert auth.call_args.kwargs["suppress_oauth_prompt"] is True

def test_json_mode_rejects_no_open_browser_without_starting_oauth(tmp_path):
    secrets = write_client_secrets(tmp_path)
    with patch("bbackup.management.gdrive_auth.auth_gdrive") as auth:
        result = CliRunner().invoke(
            bbman_cli,
            [
                "auth-gdrive",
                "--client-secrets",
                str(secrets),
                "--no-open-browser",
                "--output",
                "json",
            ],
        )

    assert result.exit_code == EXIT_USER_ERROR
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["errors"] == [
        "--no-open-browser requires text output during OAuth; use --output text or omit --no-open-browser."
    ]
    auth.assert_not_called()


def test_input_json_can_supply_client_secrets(tmp_path):
    secrets = write_client_secrets(tmp_path)
    payload = json.dumps({"client_secrets": str(secrets), "dry_run": True})
    result = CliRunner().invoke(
        bbman_cli,
        ["auth-gdrive", "--input-json", payload, "--output", "json"],
    )

    assert result.exit_code == EXIT_SUCCESS
    data = json.loads(result.output)
    assert data["data"]["client_secrets_path"] == str(secrets)


def test_no_client_secret_flag_is_exposed():
    result = CliRunner().invoke(bbman_cli, ["auth-gdrive", "--help"])

    assert result.exit_code == EXIT_SUCCESS
    assert "--client-secrets" in result.output
    assert "--client-secret " not in result.output


def test_input_json_rejects_string_port_with_json_envelope(tmp_path):
    secrets = write_client_secrets(tmp_path)
    payload = json.dumps({"client_secrets": str(secrets), "port": "53682"})
    result = CliRunner().invoke(
        bbman_cli,
        ["auth-gdrive", "--input-json", payload, "--output", "json"],
    )

    assert result.exit_code == EXIT_USER_ERROR
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["errors"] == ["port must be an integer."]


def test_input_json_output_key_controls_error_envelope(tmp_path):
    secrets = write_client_secrets(tmp_path)
    payload = json.dumps({
        "client_secrets": str(secrets),
        "port": "53682",
        "output": "json",
    })
    result = CliRunner().invoke(
        bbman_cli,
        ["auth-gdrive", "--input-json", payload],
    )

    assert result.exit_code == EXIT_USER_ERROR
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["errors"] == ["port must be an integer."]


def test_input_json_rejects_string_bool_with_json_envelope(tmp_path):
    secrets = write_client_secrets(tmp_path)
    payload = json.dumps({"client_secrets": str(secrets), "dry_run": "true"})
    result = CliRunner().invoke(
        bbman_cli,
        ["auth-gdrive", "--input-json", payload, "--output", "json"],
    )

    assert result.exit_code == EXIT_USER_ERROR
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["errors"] == ["dry_run must be a boolean."]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("client_secrets", 123),
        ("remote", ["not", "a", "remote"]),
        ("scope", {}),
    ],
)
def test_input_json_rejects_non_string_oauth_fields_before_auth(tmp_path, field, value):
    secrets = write_client_secrets(tmp_path)
    payload = {
        "client_secrets": str(secrets),
        "dry_run": False,
        field: value,
    }
    with patch("bbackup.management.gdrive_auth.auth_gdrive") as auth:
        result = CliRunner().invoke(
            bbman_cli,
            ["auth-gdrive", "--input-json", json.dumps(payload), "--output", "json"],
        )

    assert result.exit_code == EXIT_USER_ERROR
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["errors"] == [f"{field} must be a non-empty string."]
    auth.assert_not_called()
