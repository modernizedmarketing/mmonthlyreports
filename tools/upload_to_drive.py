"""
Upload a file to Google Drive using OAuth2 credentials.
Expects credentials.json in the project root (gitignored).
Token is persisted as token.pickle so re-auth isn't needed on every run.
"""
import os
import pickle
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
TOKEN_PATH = Path("token.pickle")
CREDS_PATH = Path("credentials.json")


def _get_credentials() -> Credentials:
    creds = None
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)
    return creds


def upload_to_drive(
    file_path,
    folder_id: Optional[str] = None,
    make_shareable: bool = True,
) -> dict:
    """
    Upload a file to Google Drive.
    Returns dict with 'file_id', 'web_view_link', 'name'.
    folder_id defaults to GOOGLE_DRIVE_FOLDER_ID env var if not provided.
    """
    file_path = Path(file_path)
    folder_id = folder_id or os.environ.get("GOOGLE_DRIVE_FOLDER_ID")

    creds   = _get_credentials()
    service = build("drive", "v3", credentials=creds)

    file_metadata = {
        "name": file_path.name,
        "mimeType": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
    if folder_id:
        file_metadata["parents"] = [folder_id]

    media = MediaFileUpload(
        str(file_path),
        mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        resumable=True,
    )

    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name, webViewLink",
    ).execute()

    if make_shareable:
        service.permissions().create(
            fileId=uploaded["id"],
            body={"type": "anyone", "role": "reader"},
        ).execute()

    return {
        "file_id": uploaded["id"],
        "name":    uploaded["name"],
        "web_view_link": uploaded.get("webViewLink", ""),
    }
