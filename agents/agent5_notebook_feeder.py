import os
import json
import time
import logging
from pathlib import Path
from utils.cdp_driver import get_cdp_session

logger = logging.getLogger("agent5_notebook_feeder")

def run_agent5(dry_run: bool = False):
    workspace = Path("workspace")
    source_file = workspace / "03_verified_source.txt"
    prompts_file = workspace / "04_notebook_prompts.json"

    if not source_file.exists():
        raise FileNotFoundError(f"Missing verified source file: {source_file}")
    if not prompts_file.exists():
        raise FileNotFoundError(f"Missing prompts file: {prompts_file}")

    with open(source_file, "r", encoding="utf-8") as f:
        source_text = f.read()

    with open(prompts_file, "r", encoding="utf-8") as f:
        prompts_data = json.load(f)

    steering_prompt = prompts_data.get("steering_prompt", "")
    visual_prompt = prompts_data.get("visual_prompt", "")
    combined_prompt = f"{steering_prompt}\n\nVisual Style: {visual_prompt}".strip()

    logger.info("Agent 5 starting: Ingesting source & prompts into NotebookLM")

    if dry_run:
        logger.info("[DRY RUN] Simulating NotebookLM feeding...")
        time.sleep(2)
        logger.info("[DRY RUN] Agent 5 completed successfully.")
        return

    with get_cdp_session() as (context, page):
        current_url = page.url
        logger.info(f"Connected to page: {current_url}")

        # Agar Overview Customize Dialog pehle se hi khula hua hai toh direct generation par jao
        existing_dialog = page.locator('mat-dialog-container, [role="dialog"], .cdk-overlay-pane').last
        if existing_dialog.is_visible() and existing_dialog.locator('mat-radio-button, textarea').first.is_visible():
            logger.info("Format dialog is already open on screen! Skipping re-upload and directly configuring...")
        else:
            # Fresh notebook flow
            if "notebook" not in current_url:
                logger.info("Navigating to https://notebooklm.google.com/ ...")
                page.goto("https://notebooklm.google.com/", wait_until="domcontentloaded", timeout=60000)

            logger.info("Waiting for NotebookLM dashboard to render...")
            page.wait_for_timeout(4000)

            # 1. New notebook click karo
            logger.info("Locating and clicking 'New notebook' button...")
            create_nb_selector = (
                'button:has-text("Create new"), '
                'button:has-text("New notebook"), '
                'div[role="button"]:has-text("New notebook")'
            )
            nb_btn = page.locator(create_nb_selector).first
            nb_btn.wait_for(state="visible", timeout=15000)
            nb_btn.click()
            logger.info("Successfully clicked 'New notebook'.")
            page.wait_for_timeout(4000)

            # 2. Add Sources modal
            dialog = page.locator('mat-dialog-container, [role="dialog"], .cdk-overlay-pane').last
            dialog.wait_for(state="visible", timeout=20000)

            # 3. 'Copied text' option click karo
            logger.info("Clicking 'Copied text' option...")
            copied_text_btn = dialog.locator(
                'button:has-text("Copied text"), '
                'div[role="button"]:has-text("Copied text"), '
                'div:text-is("Copied text"), '
                'span:text-is("Copied text")'
            ).first
            copied_text_btn.wait_for(state="visible", timeout=15000)
            copied_text_btn.click(force=True)
            page.wait_for_timeout(2500)

            # 4. Paste verified source into Text Source area
            logger.info("Targeting 'Paste text here' area...")
            text_input = dialog.locator(
                'textarea[placeholder*="Paste text"], '
                'textarea[aria-label*="Pasted text"], '
                'textarea[placeholder*="text"]:not([placeholder*="links"])'
            ).first

            if not text_input.is_visible():
                text_input = dialog.locator('textarea:not([placeholder*="links"]):not([placeholder*="Search"])').last

            text_input.wait_for(state="visible", timeout=15000)
            logger.info(f"Pasting verified source text ({len(source_text)} chars)...")
            text_input.fill(source_text)
            page.wait_for_timeout(2000)

            # 5. Insert button click karo
            logger.info("Clicking 'Insert' button...")
            insert_btn = dialog.locator('button:has-text("Insert"), button:text-is("Insert")').first
            insert_btn.wait_for(state="visible", timeout=10000)
            insert_btn.click(force=True)
            logger.info("Successfully clicked 'Insert' button.")

            # 6. Wait for indexing
            logger.info("Waiting 25 seconds for source ingestion & indexing...")
            page.wait_for_timeout(25000)

            # 7. Studio Panel: Video Overview click karo
            logger.info("Targeting Video Overview in Studio panel...")
            video_card = page.locator(
                'mat-card:has-text("Video Overview"), '
                'div[role="button"]:has-text("Video Overview"), '
                'button:has-text("Video Overview"), '
                'div:text-is("Video Overview")'
            ).first
            video_card.wait_for(state="visible", timeout=15000)
            video_card.click(force=True)
            logger.info("Clicked Video Overview card.")
            page.wait_for_timeout(3000)

        # 8. MODAL HANDLING: Format & Custom Steering Prompt
        modal = page.locator('mat-dialog-container, [role="dialog"], .cdk-overlay-pane').last
        modal.wait_for(state="visible", timeout=10000)

        # A. Click 'Cinematic' format explicitly
        logger.info("Selecting 'Cinematic' overview format...")
        cinematic_option = modal.locator(
            'mat-radio-button:has-text("Cinematic"), '
            '.tile-label-container:has-text("Cinematic"), '
            'div:text-is("Cinematic"), '
            'mat-radio-button:has-text("Video"), '
            'div.tile-content:has-text("Cinematic")'
        ).first

        if cinematic_option.is_visible(timeout=4000):
            cinematic_option.click(force=True)
            logger.info("Selected 'Cinematic' radio option.")
            page.wait_for_timeout(1000)
        else:
            # First radio button fallback (Video/Cinematic format tile)
            first_radio = modal.locator('mat-radio-button').first
            if first_radio.is_visible(timeout=2000):
                first_radio.click(force=True)
                logger.info("Selected default format radio button.")

        # B. Inject custom steering prompt into textarea inside modal
        logger.info("Injecting custom steering prompt into modal textarea...")
        prompt_box = modal.locator('textarea:visible, [contenteditable="true"]:visible').first
        if prompt_box.is_visible(timeout=5000):
            prompt_box.click(force=True)
            prompt_box.fill(combined_prompt)
            logger.info("Successfully injected custom prompts.")
            page.wait_for_timeout(1500)
        else:
            logger.warning("No visible prompt textarea found in modal. Continuing with default template.")

        # C. Trigger Generation inside modal
        logger.info("Clicking 'Generate' button inside modal...")
        gen_btn = modal.locator(
            'button:has-text("Generate"), '
            'button:text-is("Generate"), '
            'button:has-text("Create"), '
            'button.mat-primary'
        ).first
        
        gen_btn.wait_for(state="visible", timeout=8000)
        gen_btn.click(force=True)
        logger.info("Successfully clicked 'Generate' button.")

        page.wait_for_timeout(5000)
        logger.info("Agent 5 completed: NotebookLM generation confirmed and queued.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_agent5()