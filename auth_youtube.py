import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("auth_youtube")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


def authenticate_interactive() -> Path:
    """
    Component A: One-Time Interactive Authenticator.
    Runs OAuth consent flow in local browser, captures refresh token,
    saves persistent credentials to config/token.json, and prints channel name.
    """
    secrets_path = settings.YOUTUBE_CLIENT_SECRETS
    token_path = settings.YOUTUBE_TOKEN_PATH

    print("\n" + "=" * 65)
    print(" [YOUTUBE OAUTH SETUP] One-Time Channel Authentication")
    print("=" * 65)

    if not secrets_path.exists():
        logger.error("Client secrets file not found at: %s", secrets_path)
        print("\nERROR: Please ensure config/client_secrets.json exists with your Google Cloud OAuth credentials.")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as e:
        logger.error("Missing Google OAuth dependencies: %s", e)
        print("Run: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
        sys.exit(1)

    logger.info("Initializing OAuth flow from %s...", secrets_path.name)
    flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), scopes=SCOPES)

    print("\nA browser window will open for Google Account authentication...")
    print("Please select the Google account and channel you wish to publish to.\n")

    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    # Securely save token.json
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    logger.info("Saved persistent OAuth credentials to %s", token_path)

    # Fetch connected channel name as verification
    try:
        youtube = build("youtube", "v3", credentials=creds)
        response = youtube.channels().list(part="snippet", mine=True).execute()
        items = response.get("items", [])
        if items:
            channel_title = items[0]["snippet"].get("title", "Unknown")
            channel_id = items[0].get("id", "Unknown")
            print("\n" + "*" * 65)
            print(f" [SUCCESS] Connected YouTube Channel: {channel_title} (ID: {channel_id})")
            print(f" [SUCCESS] Token saved to: {token_path}")
            print("*" * 65 + "\n")
            logger.info("Channel confirmed: '%s' (%s)", channel_title, channel_id)
        else:
            print("\n[SUCCESS] Token saved successfully (No channels found under account).")
    except Exception as err:
        logger.warning("Token saved, but could not query channel name: %s", err)

    return token_path


if __name__ == "__main__":
    authenticate_interactive()