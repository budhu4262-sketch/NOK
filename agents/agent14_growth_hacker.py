import argparse
import datetime
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings
from agents.agent13_youtube_publisher import get_headless_authenticated_service

logger = logging.getLogger("agent14_growth_hacker")

REGISTRY_FILE = settings.CONFIG_DIR / "published_registry.json"


def load_registry() -> Dict[str, Any]:
    """Loads or initializes config/published_registry.json."""
    if REGISTRY_FILE.exists():
        try:
            return json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Could not parse published registry (%s). Rebuilding fresh.", e)
    return {"videos": []}


def save_registry(data: Dict[str, Any]) -> None:
    """Saves registry back to config/published_registry.json atomically."""
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def register_published_video(
    video_id: str,
    title: str,
    ab_test_titles: List[str],
    tags: List[str],
    published_at_iso: str,
    category_id: str = "28",
    description: str = "",
) -> None:
    """Helper called after upload to record video into published_registry.json."""
    data = load_registry()
    existing = [v for v in data.get("videos", []) if v.get("video_id") == video_id]
    if existing:
        # Update existing
        entry = existing[0]
        entry["title"] = title
        entry["ab_test_titles"] = ab_test_titles
        entry["tags"] = tags
        entry["published_at"] = published_at_iso
        entry["last_updated"] = datetime.datetime.now().isoformat()
    else:
        new_entry = {
            "video_id": video_id,
            "title": title,
            "ab_test_titles": ab_test_titles,
            "tags": tags,
            "category_id": category_id,
            "description": description[:500],
            "published_at": published_at_iso,
            "registered_at": datetime.datetime.now().isoformat(),
            "swapped_titles": [],
            "views": 0,
            "likes": 0,
            "comments": 0,
            "last_checked": None,
        }
        data.setdefault("videos", []).append(new_entry)

    save_registry(data)
    logger.info("Video %s ('%s') recorded into registry.", video_id, title)


def fetch_competitor_keyword_tags(youtube, query: str, max_tags: int = 8) -> List[str]:
    """
    Searches YouTube for top performing videos in the niche and extracts high-traffic search keywords.
    """
    new_tags = []
    try:
        search_res = youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            order="viewCount",
            maxResults=5,
        ).execute()

        for item in search_res.get("items", []):
            title = item.get("snippet", {}).get("title", "")
            # Extract clean keyword phrases (2-4 words) from viral titles
            cleaned = re.sub(r"[^\w\s]", "", title)
            words = [w.lower() for w in cleaned.split() if len(w) > 3]
            for i in range(len(words) - 1):
                phrase = f"{words[i]} {words[i+1]}"
                if len(phrase) > 5 and phrase not in new_tags:
                    new_tags.append(phrase)
                    if len(new_tags) >= max_tags:
                        break
            if len(new_tags) >= max_tags:
                break
    except Exception as e:
        logger.warning("Competitor search keyword extraction encountered error: %s", e)

    return new_tags


def optimize_video(youtube, video_entry: Dict[str, Any]) -> bool:
    """
    Performs algorithmic growth optimization on an individual video:
    1. Fetches live metrics (views, likes, comments).
    2. Dynamic SEO tag expansion (under 500 chars).
    3. A/B Title Switcher: If video public > 12 hours with low view velocity, rescues with alternate title.
    """
    video_id = video_entry.get("video_id")
    current_title = video_entry.get("title")

    if not video_id or video_id.startswith("SIMULATED_"):
        logger.info("[GROWTH HACKER] Skipping simulated video ID %s", video_id)
        return False

    try:
        # 1. Fetch live metrics
        v_res = youtube.videos().list(part="snippet,statistics", id=video_id).execute()
        items = v_res.get("items", [])
        if not items:
            logger.warning("Video %s not found on YouTube channel.", video_id)
            return False

        item = items[0]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})

        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))

        video_entry["views"] = views
        video_entry["likes"] = likes
        video_entry["comments"] = comments
        video_entry["last_checked"] = datetime.datetime.now().isoformat()

        logger.info(
            "Video Analytics [%s]: '%s' | Views: %d | Likes: %d | Comments: %d",
            video_id, current_title, views, likes, comments
        )

        needs_update = False

        # 2. Dynamic SEO & Tag Injection
        existing_tags = snippet.get("tags", video_entry.get("tags", []))
        total_tag_len = sum(len(t) for t in existing_tags)

        # Look for competitor keyword opportunities if tag space permits (< 420 chars)
        if total_tag_len < 420:
            search_query = snippet.get("title", current_title)
            extra_tags = fetch_competitor_keyword_tags(youtube, search_query, max_tags=6)
            added_tags = []
            for t in extra_tags:
                if t not in existing_tags and total_tag_len + len(t) < 480:
                    existing_tags.append(t)
                    total_tag_len += len(t)
                    added_tags.append(t)

            if added_tags:
                snippet["tags"] = existing_tags
                video_entry["tags"] = existing_tags
                needs_update = True
                logger.info("Injected %d dynamic high-traffic tags into %s: %s", len(added_tags), video_id, added_tags)

        # 3. A/B Title Switcher (Underperforming Rescue)
        # Check time since published
        published_at_str = video_entry.get("published_at")
        hours_active = 0
        if published_at_str:
            try:
                # Parse ISO UTC
                clean_iso = published_at_str.replace("Z", "+00:00")
                pub_dt = datetime.datetime.fromisoformat(clean_iso)
                now_dt = datetime.datetime.now(datetime.timezone.utc)
                hours_active = (now_dt - pub_dt).total_seconds() / 3600.0
            except Exception:
                pass

        alts = video_entry.get("ab_test_titles", [])
        # If active for > 12 hours with < 200 views (or sluggish CTR), cycle to next alternate title
        if hours_active > 12 and views < 200 and alts:
            next_title = alts.pop(0)
            logger.warning("=" * 65)
            logger.warning("[A/B TITLE RESCUE ACTIVATED] Video %s active %0.1f hours with %d views.", video_id, hours_active, views)
            logger.warning("Swapping underperforming title:")
            logger.warning("  Old Title: '%s'", current_title)
            logger.warning("  New Title: '%s'", next_title)
            logger.warning("=" * 65)

            video_entry.setdefault("swapped_titles", []).append({
                "previous_title": current_title,
                "swapped_at": datetime.datetime.now().isoformat(),
                "views_at_swap": views,
            })
            snippet["title"] = next_title[:100]
            video_entry["title"] = next_title
            needs_update = True

        # Commit update to YouTube API
        if needs_update:
            update_body = {
                "id": video_id,
                "snippet": {
                    "title": snippet.get("title"),
                    "description": snippet.get("description", ""),
                    "tags": snippet.get("tags", []),
                    "categoryId": snippet.get("categoryId", "28"),
                },
            }
            youtube.videos().update(part="snippet", body=update_body).execute()
            logger.info("Successfully updated YouTube metadata for video %s!", video_id)
            return True

    except Exception as err:
        logger.error("Error optimizing video %s: %s", video_id, err)

    return False


def run_growth_hacker(once: bool = True, interval_hours: float = 6.0) -> None:
    """
    Agent 14 Main Runner:
    Inspects all videos in published_registry.json, checks performance metrics,
    dynamically enriches tags, and executes A/B title rotations.
    """
    logger.info("Agent 14 starting: The Autonomous Growth Hacker & Algorithm Booster")

    token_path = settings.YOUTUBE_TOKEN_PATH
    if not token_path.exists():
        logger.warning("YouTube token.json not found. Run 'python auth_youtube.py' first.")
        logger.info("[MOCK MODE] Simulating Growth Hacker analysis on registry...")
        data = load_registry()
        logger.info("Found %d tracked video(s) in registry.", len(data.get("videos", [])))
        return

    youtube = get_headless_authenticated_service(token_path)
    if not youtube:
        logger.error("Failed to authenticate YouTube service for Growth Hacker.")
        return

    while True:
        data = load_registry()
        videos = data.get("videos", [])
        logger.info("Starting Growth Hacker review cycle for %d tracked video(s)...", len(videos))

        updated_any = False
        for video in videos:
            changed = optimize_video(youtube, video)
            if changed:
                updated_any = True

        save_registry(data)
        logger.info("Growth Hacker review cycle complete.")

        if once:
            break

        logger.info("Sleeping for %0.1f hours until next growth optimization cycle...", interval_hours)
        time.sleep(interval_hours * 3600)


def main():
    parser = argparse.ArgumentParser(description="Agent 14: Autonomous YouTube Growth Hacker")
    parser.add_argument("--once", action="store_true", default=True, help="Run a single growth optimization pass")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in background (default every 6 hours)")
    parser.add_argument("--interval", type=float, default=6.0, help="Check interval in hours for daemon mode (default: 6.0)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
    run_growth_hacker(once=not args.daemon, interval_hours=args.interval)


if __name__ == "__main__":
    main()