import datetime
import hashlib
import json
import logging
import re
import shutil
import sys
from pathlib import Path

# Ensure project root is in sys.path for standalone execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings

logger = logging.getLogger("agent12_asset_bundler")


def compute_sha256(file_path: Path) -> str:
    """Calculates SHA256 checksum for artifact verification."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def slugify(text: str) -> str:
    """Converts title to directory-safe slug."""
    text = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[-\s]+", "_", text)[:40]


def run_agent12() -> dict:
    """
    Agent 12: Production Asset Bundler.
    Validates file sizes, checks integrity of all run artifacts in workspace/,
    creates manifest, and archives the entire bundle into runs/<timestamp>_<topic_slug>/.
    """
    logger.info("Agent 12 starting: Bundling run assets")

    required_artifacts = [
        ("topic", settings.TOPIC_FILE, True),
        ("source", settings.SOURCE_FILE, True),
        ("verified_source", settings.VERIFIED_SOURCE_FILE, True),
        ("notebook_prompts", settings.PROMPTS_FILE, True),
        ("raw_video", settings.RAW_VIDEO_FILE, False),
        ("transcript", settings.TRANSCRIPT_FILE, True),
        ("outro", settings.OUTRO_FILE, True),
        ("voiced_video", settings.VOICED_VIDEO_FILE, False),
        ("final_video", settings.FINAL_VIDEO_FILE, True),
        ("metadata", settings.METADATA_FILE, True),
        ("thumbnail", settings.THUMBNAIL_FILE, True),
    ]

    missing_critical = []
    artifacts_manifest = {}

    for name, path, is_critical in required_artifacts:
        if path.exists():
            size_bytes = path.stat().st_size
            artifacts_manifest[name] = {
                "filename": path.name,
                "size_bytes": size_bytes,
                "size_mb": round(size_bytes / (1024 * 1024), 2),
                "sha256": compute_sha256(path),
                "status": "VALID",
            }
        else:
            if is_critical:
                missing_critical.append(name)
            artifacts_manifest[name] = {"status": "MISSING", "is_critical": is_critical}

    if missing_critical:
        raise FileNotFoundError(
            f"Agent 12 bundling failed: Missing critical artifacts: {missing_critical}"
        )

    # Read topic title for run folder slug
    topic_slug = "data_shift"
    if settings.TOPIC_FILE.exists():
        try:
            t_data = json.loads(settings.TOPIC_FILE.read_text(encoding="utf-8"))
            topic_title = t_data.get("selected_concept", {}).get("title", "data_shift")
            topic_slug = slugify(topic_title)
        except Exception:
            pass

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = settings.RUNS_DIR / f"{timestamp}_{topic_slug}"
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Build manifest
    manifest_data = {
        "timestamp": timestamp,
        "topic_slug": topic_slug,
        "archive_directory": str(archive_dir.resolve()),
        "total_artifacts": len([a for a in artifacts_manifest.values() if a.get("status") == "VALID"]),
        "artifacts": artifacts_manifest,
        "ready_for_publishing": True,
    }

    # Save manifest into workspace
    settings.MANIFEST_FILE.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    # Copy all valid assets into historical archive directory
    logger.info("Archiving assets to %s...", archive_dir)
    for item in settings.WORKSPACE_DIR.iterdir():
        if item.is_file():
            shutil.copy2(item, archive_dir / item.name)

    logger.info("Agent 12 completed: Manifest created -> %s, Archived to -> %s", 
                settings.MANIFEST_FILE, archive_dir)
    return manifest_data


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_agent12()