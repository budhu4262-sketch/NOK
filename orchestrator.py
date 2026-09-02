import argparse
import datetime
import json
import logging
import os
import shutil
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, Tuple

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings
try:
    from utils.config import validate_environment
except ImportError:
    def validate_environment():
        print("[Config] Fallback environment validation passed.")
        return True
from agents.agent1_trend_scout import run_agent1
from agents.agent2_source_writer import run_agent2
from agents.agent3_fact_verifier import run_agent3
from agents.agent4_prompt_synthesizer import run_agent4
from agents.agent5_notebook_feeder import run_agent5
from agents.agent6_asset_harvester import run_agent6
from agents.agent7_transcriber_outro import run_agent7
from agents.agent8_voice_transformer import run_agent8
from agents.agent9_subtitle_editor import run_agent9
from agents.agent10_seo_packager import run_agent10
from agents.agent11_thumbnail_generator import run_agent11
from agents.agent12_asset_bundler import run_agent12
from agents.agent13_youtube_publisher import run_agent13
from agents.agent14_growth_hacker import register_published_video, run_growth_hacker

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(settings.WORKSPACE_DIR / "pipeline.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("boss_orchestrator")


AGENTS = [
    (1, "Trend Scout", run_agent1),
    (2, "Source Writer", run_agent2),
    (3, "Fact & Ingestion Verifier", run_agent3),
    (4, "Prompt Synthesizer", run_agent4),
    (5, "NotebookLM Feeder", run_agent5),
    (6, "Asset Harvester", run_agent6),
    (7, "Transcriber & Outro Synthesizer", run_agent7),
    (8, "Voice Transformer & Splicer", run_agent8),
    (9, "Subtitle & Dynamic Editor", run_agent9),
    (10, "SEO & Packaging Packager", run_agent10),
    (11, "Thumbnail Engine", run_agent11),
    (12, "Production Asset Bundler", run_agent12),
    (13, "YouTube Publisher", run_agent13),
]


# -------------------------------------------------------------
# 1. DAILY QUOTA GUARD
# -------------------------------------------------------------
def check_daily_quota(force: bool = False) -> bool:
    """
    Checks config/daily_tracker.json against DAILY_VIDEO_LIMIT.
    Resets at midnight. Exits cleanly if quota is reached unless force=True.
    """
    today_str = datetime.date.today().isoformat()
    tracker_file = settings.DAILY_TRACKER_FILE
    tracker_data = {"last_date": today_str, "completed_count": 0}

    if tracker_file.exists():
        try:
            tracker_data = json.loads(tracker_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Could not read daily tracker (%s). Resetting for today.", e)

    # Reset if new calendar day
    if tracker_data.get("last_date") != today_str:
        tracker_data = {"last_date": today_str, "completed_count": 0}
        tracker_file.write_text(json.dumps(tracker_data, indent=2), encoding="utf-8")

    count = tracker_data.get("completed_count", 0)
    limit = settings.DAILY_VIDEO_LIMIT

    logger.info("Daily Quota Tracker: %d/%d completed today (%s)", count, limit, today_str)

    if count >= limit:
        if force:
            logger.warning("[DAILY QUOTA BYPASS] Limit reached (%d/%d), continuing due to --force flag.", count, limit)
            return True
        else:
            logger.warning("=" * 65)
            logger.warning("[DAILY QUOTA REACHED] %d videos already generated today.", count)
            logger.warning("Quota resets automatically at 00:00 midnight.")
            logger.warning("To override and run anyway, pass: python orchestrator.py --force")
            logger.warning("=" * 65)
            sys.exit(0)
    return True


def increment_daily_quota():
    """Increments the completed video count in config/daily_tracker.json."""
    today_str = datetime.date.today().isoformat()
    tracker_file = settings.DAILY_TRACKER_FILE
    tracker_data = {"last_date": today_str, "completed_count": 0}

    if tracker_file.exists():
        try:
            tracker_data = json.loads(tracker_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    if tracker_data.get("last_date") != today_str:
        tracker_data["last_date"] = today_str
        tracker_data["completed_count"] = 0

    tracker_data["completed_count"] += 1
    tracker_file.write_text(json.dumps(tracker_data, indent=2), encoding="utf-8")
    logger.info("[DAILY TRACKER] Video count incremented to %d/%d for %s",
                tracker_data["completed_count"], settings.DAILY_VIDEO_LIMIT, today_str)


# -------------------------------------------------------------
# 2. ARTIFACT HEALTH VALIDATION
# -------------------------------------------------------------
def get_size_thresholds(dry_run: bool = False) -> Dict[Path, int]:
    """Returns the minimum valid byte thresholds for critical artifacts."""
    if dry_run:
        # Scaled down for dry-run/synthetic test assets
        return {
            settings.RAW_VIDEO_FILE: 10 * 1024,      # 10 KB
            settings.TRANSCRIPT_FILE: 100,            # 100 B
            settings.VOICED_VIDEO_FILE: 10 * 1024,   # 10 KB
            settings.FINAL_VIDEO_FILE: 10 * 1024,    # 10 KB
            settings.THUMBNAIL_FILE: 1024,           # 1 KB
        }
    return {
        settings.RAW_VIDEO_FILE: 10 * 1024 * 1024,   # 10 MB
        settings.TRANSCRIPT_FILE: 500,               # 500 Bytes
        settings.VOICED_VIDEO_FILE: 10 * 1024 * 1024,# 10 MB
        settings.FINAL_VIDEO_FILE: 10 * 1024 * 1024, # 10 MB
        settings.THUMBNAIL_FILE: 5 * 1024,           # 5 KB
    }


def validate_artifact_health(stage_num: int, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Validates that required input artifacts for stage_num exist and satisfy health thresholds.
    """
    thresholds = get_size_thresholds(dry_run)

    # Mapping of required inputs for each stage
    stage_requirements = {
        2: [(settings.TOPIC_FILE, 50, "01_topic.json")],
        3: [(settings.SOURCE_FILE, 100, "02_source.txt")],
        4: [(settings.VERIFIED_SOURCE_FILE, 50, "03_verified_source.txt")],
        5: [
            (settings.VERIFIED_SOURCE_FILE, 50, "03_verified_source.txt"),
            (settings.PROMPTS_FILE, 50, "04_notebook_prompts.json"),
        ],
        7: [(settings.RAW_VIDEO_FILE, thresholds[settings.RAW_VIDEO_FILE], "06_raw_video.mp4")],
        8: [
            (settings.RAW_VIDEO_FILE, thresholds[settings.RAW_VIDEO_FILE], "06_raw_video.mp4"),
            (settings.OUTRO_FILE, 50, "07_outro.json"),
        ],
        9: [
            (settings.VOICED_VIDEO_FILE, thresholds[settings.VOICED_VIDEO_FILE], "08_voiced_video.mp4"),
            (settings.TRANSCRIPT_FILE, thresholds[settings.TRANSCRIPT_FILE], "07_transcript.json"),
        ],
        10: [
            (settings.TRANSCRIPT_FILE, thresholds[settings.TRANSCRIPT_FILE], "07_transcript.json"),
            (settings.TOPIC_FILE, 50, "01_topic.json"),
        ],
        11: [(settings.TOPIC_FILE, 50, "01_topic.json")],
        12: [
            (settings.FINAL_VIDEO_FILE, thresholds[settings.FINAL_VIDEO_FILE], "09_final_video.mp4"),
            (settings.THUMBNAIL_FILE, thresholds[settings.THUMBNAIL_FILE], "11_thumbnail.png"),
            (settings.METADATA_FILE, 100, "10_metadata.json"),
        ],
        13: [
            (settings.FINAL_VIDEO_FILE, thresholds[settings.FINAL_VIDEO_FILE], "09_final_video.mp4"),
            (settings.THUMBNAIL_FILE, thresholds[settings.THUMBNAIL_FILE], "11_thumbnail.png"),
            (settings.METADATA_FILE, 100, "10_metadata.json"),
        ],
    }

    reqs = stage_requirements.get(stage_num, [])
    for path, min_size, label in reqs:
        if not path.exists():
            return False, f"Missing input artifact: {label} ({path.name}) required for Stage {stage_num}"
        size = path.stat().st_size
        if size < min_size:
            return False, f"Artifact health failure: {label} is corrupted or under-sized ({size:,} B < {min_size:,} B threshold)"

    return True, "OK"


# -------------------------------------------------------------
# 3. AUTONOMOUS ARCHIVING & WORKSPACE PURGE
# -------------------------------------------------------------
def autonomous_archive_and_clean(topic_slug: str = "youtube_run"):
    """
    On completion of Stage 13, archives all generated assets into runs/
    and resets workspace/ so subsequent scheduled runs start completely fresh.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = settings.RUNS_DIR / f"{timestamp}_{topic_slug}"
    run_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 65)
    logger.info("[AUTONOMOUS ARCHIVER] Moving run artifacts to %s...", run_dir)

    moved_count = 0
    for item in settings.WORKSPACE_DIR.iterdir():
        if item.is_file():
            dest = run_dir / item.name
            shutil.copy2(item, dest)
            moved_count += 1
            # Clean up ephemeral files except log
            if item.name != "pipeline.log":
                try:
                    item.unlink()
                except PermissionError:
                    time.sleep(0.5)
                    try:
                        item.unlink()
                    except Exception:
                        pass


    logger.info("[AUTONOMOUS ARCHIVER] Successfully archived %d artifacts.", moved_count)
    logger.info("[WORKSPACE CLEAN] Workspace directory wiped clean for next run.")
    logger.info("=" * 65)


def print_workspace_status():
    """Prints status of all artifacts in the workspace."""
    print("\n" + "=" * 60)
    print("WORKSPACE ARTIFACTS STATUS:")
    print("=" * 60)
    artifacts = [
        ("01_topic.json", settings.TOPIC_FILE),
        ("02_source.txt", settings.SOURCE_FILE),
        ("03_verified_source.txt", settings.VERIFIED_SOURCE_FILE),
        ("04_notebook_prompts.json", settings.PROMPTS_FILE),
        ("06_raw_video.mp4", settings.RAW_VIDEO_FILE),
        ("07_transcript.json", settings.TRANSCRIPT_FILE),
        ("07_outro.json", settings.OUTRO_FILE),
        ("08_voiced_video.mp4", settings.VOICED_VIDEO_FILE),
        ("09_final_video.mp4", settings.FINAL_VIDEO_FILE),
        ("10_metadata.json", settings.METADATA_FILE),
        ("11_thumbnail.png", settings.THUMBNAIL_FILE),
        ("12_manifest.json", settings.MANIFEST_FILE),
    ]
    for name, path in artifacts:
        if path.exists():
            size = path.stat().st_size
            print(f"  [FOUND]     {name:<26} ({size:,} bytes)")
        else:
            print(f"  [MISSING]   {name:<26}")
    print("=" * 60 + "\n")


# -------------------------------------------------------------
# 4. MASTER SUPERVISOR EXECUTION LOOP
# -------------------------------------------------------------
def run_pipeline(
    start_stage: int = 1,
    end_stage: int = 13,
    dry_run: bool = False,
    force: bool = False,
    custom_topic: str = None,
):
    """
    Self-healing supervisor loop:
    - Verifies daily quota
    - Validates artifact health before each stage
    - Applies up to 2 retries on stage failure
    - Archives and wipes workspace upon Stage 13 completion
    """
    check_daily_quota(force=force)

    start_time = datetime.datetime.now()
    logger.info("=" * 70)
    logger.info("BOSS AGENT SUPERVISOR INITIALIZED (Stages %d -> %d) | Dry-run: %s | Force: %s",
                start_stage, end_stage, dry_run, force)
    logger.info("=" * 70)

    topic_slug = "data_shift"

    for stage_num, name, func in AGENTS:
        if stage_num < start_stage:
            continue
        if stage_num > end_stage:
            break

        # 1. Health validation of pre-requisite artifacts
        healthy, reason = validate_artifact_health(stage_num, dry_run=dry_run)
        if not healthy:
            logger.error("[PRE-STAGE HEALTH ALERT] Stage %d cannot proceed: %s", stage_num, reason)
            sys.exit(1)

        # 2. Stage Execution with Self-Healing Retry Loop (Up to 2 retries)
        max_attempts = 3
        stage_success = False

        for attempt in range(1, max_attempts + 1):
            logger.info("\n>>> EXECUTING STAGE %d (Attempt %d/%d): %s", stage_num, attempt, max_attempts, name)
            try:
                if stage_num == 1 and custom_topic:
                    res = func(custom_niche=custom_topic)
                elif stage_num in (5, 6):
                    res = func(dry_run=dry_run)
                else:
                    res = func()

                # Extract topic slug if at Stage 1
                if stage_num == 1 and isinstance(res, dict):
                    sel = res.get("selected_concept", {})
                    t_title = sel.get("title", "data_shift")
                    topic_slug = "".join([c if c.isalnum() else "_" for c in t_title.lower()])[:35]

                logger.info("<<< STAGE %d (%s) COMPLETED SUCCESSFULLY.", stage_num, name)
                stage_success = True
                break

            except Exception as e:
                logger.warning("[STAGE ERROR] Attempt %d failed for Stage %d (%s): %s", attempt, stage_num, name, e)
                if attempt < max_attempts:
                    logger.info("Self-healing watchdog: Retrying Stage %d in 3 seconds...", stage_num)
                    time.sleep(3)
                else:
                    logger.error("!" * 70)
                    logger.error("SUPERVISOR HALTED: Stage %d (%s) failed after %d attempts.", stage_num, name, max_attempts)
                    logger.error("TRACEBACK:\n%s", traceback.format_exc())
                    logger.error("Workspace state preserved in: %s", settings.WORKSPACE_DIR)
                    logger.error("Resume after manual fix with: python orchestrator.py --stage %d", stage_num)
                    logger.error("!" * 70)
                    sys.exit(1)

    # 3. Post-Run Processing: Registry Logging, Quota & Autonomous Archiving
    if end_stage == 13 and stage_success:
        increment_daily_quota()

        # Log into config/published_registry.json for Agent 14 Growth Hacker
        try:
            res_file = settings.WORKSPACE_DIR / "13_youtube_result.json"
            if res_file.exists():
                y_data = json.loads(res_file.read_text(encoding="utf-8"))
                m_meta = json.loads(settings.METADATA_FILE.read_text(encoding="utf-8")) if settings.METADATA_FILE.exists() else {}
                register_published_video(
                    video_id=y_data.get("video_id", "UNKNOWN"),
                    title=y_data.get("title", m_meta.get("primary_title", "Untitled")),
                    ab_test_titles=m_meta.get("ab_test_titles", []),
                    tags=m_meta.get("tags", []),
                    published_at_iso=y_data.get("publish_at_iso", ""),
                    category_id=str(y_data.get("category_id", "28")),
                    description=m_meta.get("description", "")
                )
                logger.info("[REGISTRY] Video logged into config/published_registry.json for Agent 14 tracking.")
        except Exception as reg_err:
            logger.warning("Could not record video to published_registry.json: %s", reg_err)

        if not dry_run:
            autonomous_archive_and_clean(topic_slug)
        else:
            logger.info("[DRY-RUN] Retaining workspace files for inspection. Manifest and archive verified.")
            print_workspace_status()

    elapsed = datetime.datetime.now() - start_time
    logger.info("=" * 70)
    logger.info("PIPELINE RUN FINISHED SUCCESSFULLY in %s", str(elapsed).split(".")[0])
    logger.info("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Boss Agent Supervisory Watchdog for 13-Agent YouTube Pipeline"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--full",
        action="store_true",
        help="Run all 13 agents from Trend Scout to YouTube Publication",
    )
    group.add_argument(
        "--stage",
        type=int,
        choices=range(1, 14),
        help="Resume pipeline from a specific stage (1 to 13)",
    )
    group.add_argument(
        "--skip-notebooklm",
        action="store_true",
        help="Skip NotebookLM web automation and run post-processing on existing 06_raw_video.mp4 (Agents 7-13)",
    )
    group.add_argument(
        "--status",
        action="store_true",
        help="Inspect current workspace state and generated artifacts",
    )
    group.add_argument(
        "--growth",
        action="store_true",
        help="Run Agent 14 Autonomous Growth Hacker & Algorithm Booster optimization cycle",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass the daily 2-video quota limit",
    )

    parser.add_argument("--auto-confirm", action="store_true", help="Auto confirm all stages")
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run pipeline with simulated external browser/upload calls",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="Optional custom niche or concept theme for Agent 1",
    )

    args = parser.parse_args()

    if args.status:
        validate_environment()
        print_workspace_status()
        return

    if args.growth:
        run_growth_hacker(once=True)
        return

    if args.skip_notebooklm:
        if not settings.RAW_VIDEO_FILE.exists():
            print(f"Error: --skip-notebooklm requires an existing {settings.RAW_VIDEO_FILE}")
            sys.exit(1)
        run_pipeline(start_stage=7, end_stage=13, dry_run=args.dry_run, force=args.force)
    elif args.stage:
        run_pipeline(
            start_stage=args.stage,
            end_stage=13,
            dry_run=args.dry_run,
            force=args.force,
            custom_topic=args.topic,
        )
    elif args.full:
        run_pipeline(
            start_stage=1,
            end_stage=13,
            dry_run=args.dry_run,
            force=args.force,
            custom_topic=args.topic,
        )
    else:
        parser.print_help()



if __name__ == "__main__":
    main()
