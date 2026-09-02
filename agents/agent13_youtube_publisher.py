import datetime
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Tuple, Optional
from zoneinfo import ZoneInfo
from googleapiclient.http import MediaFileUpload

# Ensure project root is in sys.path for standalone execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings

logger = logging.getLogger("agent13_youtube_publisher")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


def calculate_next_ist_publish_slot(min_buffer_minutes: int = 45) -> Tuple[datetime.datetime, datetime.datetime, str]:
    """
    Calculates the next immediate optimal publish slot in Asia/Kolkata (IST):
    - Slot 1: 11:45 PM IST (23:45 IST = 18:15 UTC)
    - Slot 2: 02:00 AM IST (02:00 IST = 20:30 UTC)
    Guarantees at least min_buffer_minutes (45m) buffer from now for HD/4K encoding.
    Returns: (slot_ist, slot_utc, iso_utc_string)
    """
    tz_ist = ZoneInfo("Asia/Kolkata")
    now_ist = datetime.datetime.now(tz_ist)
    earliest_allowed = now_ist + datetime.timedelta(minutes=min_buffer_minutes)

    candidates = []
    # Check slots across today, tomorrow, and day after
    for day_offset in range(0, 3):
        base_date = now_ist.date() + datetime.timedelta(days=day_offset)
        # Slot 2: 02:00 AM IST
        candidates.append(datetime.datetime.combine(base_date, datetime.time(2, 0), tzinfo=tz_ist))
        # Slot 1: 11:45 PM IST
        candidates.append(datetime.datetime.combine(base_date, datetime.time(23, 45), tzinfo=tz_ist))

    candidates.sort()

    for c in candidates:
        if c >= earliest_allowed:
            utc_dt = c.astimezone(datetime.timezone.utc)
            iso_utc = utc_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            return c, utc_dt, iso_utc

    # Fallback to 2 hours from now
    fallback = now_ist + datetime.timedelta(hours=2)
    utc_f = fallback.astimezone(datetime.timezone.utc)
    return fallback, utc_f, utc_f.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def get_headless_authenticated_service(token_path: Path):
    """
    Component B: 100% Headless Authentication.
    Reads persistent credentials from config/token.json, automatically refreshes
    expired tokens via google.auth.transport.requests.Request(), and never prompts the user.
    """
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    if not token_path.exists():
        return None

    try:
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            logger.info("Access token expired. Refreshing headless via refresh_token...")
            creds.refresh(Request())
            # Save refreshed credentials back to token.json
            token_path.write_text(creds.to_json(), encoding="utf-8")
            logger.info("Refreshed credentials saved to %s", token_path)
        if creds and creds.valid:
            return build("youtube", "v3", credentials=creds)
    except Exception as e:
        logger.error("Failed to load or refresh token from %s: %s", token_path, e)
        return None
    return None


def run_agent13(scheduled_time_iso: Optional[str] = None, privacy_status: Optional[str] = None) -> dict:
    """
    Agent 13: Headless YouTube Publisher with Automated Dual-Slot Scheduling (IST).
    Uploads 09_final_video.mp4, attaches 11_thumbnail.png, applies 10_metadata.json,
    schedules publication at either 11:45 PM IST or 02:00 AM IST,
    and writes upload results to workspace/13_youtube_result.json.
    """
    logger.info("Agent 13 starting: Headless YouTube Publisher & Smart Scheduler")

    result_file = settings.WORKSPACE_DIR / "13_youtube_result.json"

    # Verify input assets exist
    if not settings.FINAL_VIDEO_FILE.exists():
        raise FileNotFoundError(f"Missing final video: {settings.FINAL_VIDEO_FILE}. Run Agent 9 first.")
    if not settings.THUMBNAIL_FILE.exists():
        raise FileNotFoundError(f"Missing thumbnail: {settings.THUMBNAIL_FILE}. Run Agent 11 first.")
    if not settings.METADATA_FILE.exists():
        raise FileNotFoundError(f"Missing metadata: {settings.METADATA_FILE}. Run Agent 10 first.")

    metadata = json.loads(settings.METADATA_FILE.read_text(encoding="utf-8"))
    title = metadata.get("primary_title", metadata.get("titles", ["Data Visualization"])[0])
    description = metadata.get("description", "")
    tags = metadata.get("tags", ["data visualization", "statistics"])
    category_id = metadata.get("category_id", settings.YOUTUBE_CATEGORY_ID)
    privacy = privacy_status or settings.YOUTUBE_PRIVACY_STATUS

    # Calculate smart scheduled publish slot in IST
    slot_ist, slot_utc, auto_iso_publish = calculate_next_ist_publish_slot(min_buffer_minutes=45)
    final_publish_iso = scheduled_time_iso or auto_iso_publish

    print("\n" + "=" * 65)
    print(" [SMART IST SCHEDULING ENGINE] Automated Dual-Slot Assignment")
    print("=" * 65)
    print(f"  Target IST Slot  : {slot_ist.strftime('%Y-%m-%d %I:%M %p %Z')}")
    print(f"  Target UTC Time  : {slot_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  ISO 8601 Publish : {final_publish_iso}")
    print(f"  Buffer Guaranteed: > 45 minutes for YouTube 4K/HD Processing")
    print("=" * 65 + "\n")

    token_path = settings.YOUTUBE_TOKEN_PATH

    # Check for token.json (Headless Auth Check)
    if not token_path.exists():
        logger.warning("=" * 65)
        logger.warning("[HEADLESS NOTICE] config/token.json not found.")
        logger.warning("To link your YouTube channel, run once in your terminal:")
        logger.warning("    python auth_youtube.py")
        logger.warning("Running Agent 13 in SIMULATED mode for this pipeline run.")
        logger.warning("=" * 65)

        simulated_id = "SIMULATED_VID_" + str(abs(hash(title)))[-8:]
        sim_result = {
            "status": "SIMULATED_SUCCESS",
            "video_id": simulated_id,
            "url": f"https://youtu.be/{simulated_id}",
            "title": title,
            "category_id": category_id,
            "privacy_status": "private",
            "scheduled_time_ist": slot_ist.strftime("%Y-%m-%d %I:%M %p %Z"),
            "scheduled_time_utc": slot_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "publish_at_iso": final_publish_iso,
            "thumbnail": str(settings.THUMBNAIL_FILE),
            "note": "Run 'python auth_youtube.py' to enable live headless uploads.",
        }
        result_file.write_text(json.dumps(sim_result, indent=2), encoding="utf-8")
        logger.info("Agent 13 (Simulated): %s (Scheduled for %s)", sim_result["url"], sim_result["scheduled_time_ist"])
        return sim_result

    # Attempt Live Headless Upload via token.json
    youtube = get_headless_authenticated_service(token_path)
    if not youtube:
        logger.warning("Could not initialize authenticated YouTube client from token.json. Using simulated mode.")
        simulated_id = "SIMULATED_VID_" + str(abs(hash(title)))[-8:]
        sim_result = {
            "status": "SIMULATED_FALLBACK",
            "video_id": simulated_id,
            "url": f"https://youtu.be/{simulated_id}",
            "title": title,
            "privacy_status": "private",
            "scheduled_time_ist": slot_ist.strftime("%Y-%m-%d %I:%M %p %Z"),
            "publish_at_iso": final_publish_iso,
            "note": "Token refresh failed; re-run 'python auth_youtube.py'.",
        }
        result_file.write_text(json.dumps(sim_result, indent=2), encoding="utf-8")
        return sim_result

    try:
        # Sanitize and strictly enforce YouTube's 400-char cumulative tag limit
        clean_tags = []
        tot_tag_len = 0
        for t in tags:
            clean_t = re.sub(r"[^\w\s\-\.]", "", str(t)).strip()
            if clean_t and tot_tag_len + len(clean_t) + 1 <= 400:
                clean_tags.append(clean_t)
                tot_tag_len += len(clean_t) + 1

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": clean_tags,
                "categoryId": str(category_id),
            },
            "status": {
                "privacyStatus": "private",
                "publishAt": final_publish_iso,
                "selfDeclaredMadeForKids": False,
            },
        }

        logger.info("Uploading video file (%0.2f MB) with scheduled publishAt=%s...",
                    settings.FINAL_VIDEO_FILE.stat().st_size / (1024 * 1024), final_publish_iso)
        media = MediaFileUpload(str(settings.FINAL_VIDEO_FILE), chunksize=1024 * 1024 * 5, resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

        response = None
        while response is None:
            status_chunk, response = request.next_chunk()
            if status_chunk:
                logger.info("Upload progress: %d%%", int(status_chunk.progress() * 100))

        video_id = response.get("id")
        video_url = f"https://youtu.be/{video_id}"
        logger.info("Video uploaded successfully! Video ID: %s (URL: %s)", video_id, video_url)

        # Attach custom thumbnail
        logger.info("Uploading thumbnail: %s...", settings.THUMBNAIL_FILE.name)
        thumb_media = MediaFileUpload(str(settings.THUMBNAIL_FILE), mimetype="image/png")
        youtube.thumbnails().set(videoId=video_id, media_body=thumb_media).execute()
        logger.info("Thumbnail attached successfully!")

        live_result = {
            "status": "PUBLISHED_SCHEDULED_SUCCESS",
            "video_id": video_id,
            "url": video_url,
            "title": title,
            "privacy_status": "private",
            "scheduled_time_ist": slot_ist.strftime("%Y-%m-%d %I:%M %p %Z"),
            "scheduled_time_utc": slot_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "publish_at_iso": final_publish_iso,
            "category_id": category_id,
        }
        result_file.write_text(json.dumps(live_result, indent=2), encoding="utf-8")
        logger.info("Agent 13 completed: Video scheduled -> %s (Publish at %s)", video_url, live_result["scheduled_time_ist"])
        return live_result

    except Exception as err:
        logger.error("Headless YouTube scheduled upload encountered an error: %s", err)
        raise




if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_agent13()