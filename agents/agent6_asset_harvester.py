import os
import time
import logging
from pathlib import Path
from utils.cdp_driver import get_cdp_session

logger = logging.getLogger("agent6_asset_harvester")

def run_agent6(dry_run: bool = False):
    workspace = Path("workspace")
    raw_video_dest = workspace / "06_raw_video.mp4"

    logger.info("Agent 6 starting: Smart Detection Harvester (2m Poll | 60m + 30m Grace Buffer)")

    if dry_run:
        logger.info("[DRY RUN] Simulating asset harvesting...")
        if not raw_video_dest.exists():
            try:
                import subprocess
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=0x0F172A:s=1920x1080:d=5",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:duration=5",
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    str(raw_video_dest),
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info("[DRY RUN] Generated synthetic raw video: %s", raw_video_dest)
            except Exception as e:
                logger.warning("[DRY RUN] Could not generate synthetic video with ffmpeg: %s", e)
                raw_video_dest.write_bytes(b"\x00" * 20480)
        return


    # Agar video pehle se mojud hai toh skip
    if raw_video_dest.exists() and raw_video_dest.stat().st_size > 1024 * 1024:
        logger.info(f"Raw video already present ({raw_video_dest.stat().st_size / (1024*1024):.2f} MB). Skipping.")
        return

    poll_interval = 120       # Har 2 minute (120s) me check karega
    base_limit = 3600         # 1 ghanta (60 mins)
    max_grace_limit = 5400    # 1 ghanta + 30 mins grace = 90 mins max
    elapsed = 0

    while elapsed < max_grace_limit:
        try:
            with get_cdp_session() as (context, page):
                logger.info(f"Connected to Chrome session. Monitoring Video Overview live...")

                while elapsed < max_grace_limit:
                    # 1. Heartbeat ping - Keeps Chrome socket alive
                    try:
                        page.evaluate("() => document.title")
                    except Exception:
                        pass

                    # 2. Check generation state
                    spinner = page.locator('mat-progress-spinner, mat-progress-bar, [role="progressbar"], div:has-text("Generating")').first
                    is_generating = spinner.is_visible()

                    # 3. Detect 3-dots action menu
                    more_menu = page.locator(
                        'button[aria-label*="More options"], '
                        'button[aria-label*="more"], '
                        'mat-icon:has-text("more_vert"), '
                        'button:has-text("more_vert")'
                    ).last

                    # Video ready condition
                    if not is_generating and more_menu.is_visible():
                        logger.info(">>> [SUCCESS] Video render detected on Google NotebookLM! Starting auto-download...")
                        try:
                            more_menu.click(force=True)
                            page.wait_for_timeout(1500)

                            download_btn = page.locator(
                                'button:has-text("Download"), '
                                'div[role="menuitem"]:has-text("Download"), '
                                'span:text-is("Download")'
                            ).first

                            with page.expect_download(timeout=60000) as download_info:
                                download_btn.click(force=True)

                            download = download_info.value
                            logger.info("Downloading MP4 asset directly into workspace...")
                            download.save_as(str(raw_video_dest))

                            if raw_video_dest.exists() and raw_video_dest.stat().st_size > 1024 * 1024:
                                logger.info(f"Agent 6 completed: Video successfully downloaded -> {raw_video_dest} ({raw_video_dest.stat().st_size / (1024*1024):.2f} MB)")
                                return
                        except Exception as e:
                            logger.warning(f"Download trigger hiccup: {e}. Retrying in next 2m cycle...")

                    # Logging & Grace Period status
                    mins_passed = elapsed // 60
                    if elapsed >= base_limit:
                        logger.warning(f"[{mins_passed}m passed] 1 Hour reached! Running inside 30-minute grace window...")
                    else:
                        logger.info(f"[{mins_passed}m / 60m] Video rendering on Google TPUs... Heartbeat active.")

                    page.wait_for_timeout(poll_interval * 1000)
                    elapsed += poll_interval

        except Exception as conn_err:
            logger.warning(f"CDP connection interrupted: {conn_err}. Re-establishing session in 10s...")
            time.sleep(10)
            elapsed += 10

    # Agar 90 minute ke baad bhi nahi bani
    logger.error(">>> [TIMEOUT] Max limit (90 mins) reached. Generation stuck on NotebookLM.")
    raise TimeoutError("NotebookLM generation exceeded 90 minutes limit. Restarting session required.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_agent6()