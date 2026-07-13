"""
YouTube upload module with OAuth2 authentication.
On first run it opens a browser for user consent and saves a token.
Subsequent runs use the saved token silently (auto-refreshed).
Uses the YouTube Data API v3 to upload and schedule videos.
"""
import os
import config
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _get_authenticated_service():
    creds = None

    if os.path.exists(config.YT_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(config.YT_TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                config.YT_CLIENT_SECRETS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(config.YT_TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: list,
    publish_at_iso: str,
) -> str:
    """
    Uploads video_path to YouTube as a scheduled private video.
    publish_at_iso: ISO 8601 UTC string, e.g. "2024-01-15T16:00:00Z"
    Returns the YouTube video ID.
    """
    youtube = _get_authenticated_service()

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "22",  # People & Blogs - works for this format
        },
        "status": {
            "privacyStatus": "private",
            "publishAt": publish_at_iso,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Upload progress: {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"  Uploaded: https://youtu.be/{video_id} (scheduled: {publish_at_iso})")
    return video_id
