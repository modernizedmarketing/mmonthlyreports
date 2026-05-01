from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import google_workspace


def test_extract_file_id_accepts_urls_and_raw_ids():
    assert google_workspace.extract_file_id("abc123") == "abc123"
    assert (
        google_workspace.extract_file_id("https://docs.google.com/spreadsheets/d/abc123/edit#gid=0")
        == "abc123"
    )
    assert google_workspace.extract_file_id("https://drive.google.com/open?id=xyz789") == "xyz789"
    assert (
        google_workspace.extract_file_id("https://drive.google.com/drive/folders/folder123?usp=drive_link")
        == "folder123"
    )


def test_get_workspace_credentials_uses_service_account_file(monkeypatch, tmp_path):
    service_account_path = tmp_path / "service-account.json"
    service_account_path.write_text("{}", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_from_service_account_file(filename, scopes):
        captured["filename"] = filename
        captured["scopes"] = list(scopes)
        return SimpleNamespace(valid=True)

    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_FILE", str(service_account_path))
    monkeypatch.setattr(
        google_workspace.service_account.Credentials,
        "from_service_account_file",
        fake_from_service_account_file,
    )

    creds = google_workspace.get_workspace_credentials()

    assert creds.valid is True
    assert captured["filename"] == str(service_account_path)
    assert captured["scopes"] == google_workspace.WORKSPACE_SCOPES


def test_get_workspace_credentials_requires_existing_service_account_file(monkeypatch, tmp_path):
    missing_path = tmp_path / "missing.json"
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_FILE", str(missing_path))

    with pytest.raises(FileNotFoundError, match="GOOGLE_SERVICE_ACCOUNT_FILE points to a missing file"):
        google_workspace.get_workspace_credentials()


def test_get_workspace_credentials_requires_local_credentials_when_no_token(monkeypatch, tmp_path):
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_FILE", raising=False)

    with pytest.raises(FileNotFoundError, match="Google Workspace credentials not found"):
        google_workspace.get_workspace_credentials(
            token_path=tmp_path / "token_workspace.pickle",
            creds_path=tmp_path / "credentials.json",
        )
