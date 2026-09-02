import logging
import time
from contextlib import contextmanager
from typing import Generator, Tuple
from playwright.sync_api import sync_playwright, BrowserContext, Page
from config import settings

logger = logging.getLogger("cdp_driver")


@contextmanager
def get_cdp_session(
    cdp_url: str = settings.CDP_URL,
    target_url_pattern: str = "notebooklm.google.com",
    auto_navigate: bool = True,
) -> Generator[Tuple[BrowserContext, Page], None, None]:
    """
    Connects to an existing user-authenticated Chrome session via CDP on port 9222.
    Reuses existing NotebookLM tabs or creates a new tab in the active user profile.
    Disconnects safely without closing the user's Chrome instance.
    """
    logger.info("Connecting to Chrome CDP at %s...", cdp_url)
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.connect_over_cdp(cdp_url)
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to Chrome over CDP at {cdp_url}.\n"
                f"Ensure Google Chrome is launched with remote debugging enabled:\n"
                f'  chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\\Users\\dell\\AppData\\Local\\Google\\Chrome\\User Data"'
            ) from e

        contexts = browser.contexts
        context = contexts[0] if contexts else browser.new_context()

        target_page = None
        for p in context.pages:
            if target_url_pattern and target_url_pattern in p.url:
                logger.info("Found existing tab matching '%s': %s", target_url_pattern, p.url)
                target_page = p
                break

        if not target_page:
            logger.info("No matching tab found. Opening a new tab...")
            target_page = context.new_page()
            if auto_navigate:
                logger.info("Navigating to %s...", settings.NOTEBOOKLM_URL)
                target_page.goto(
                    settings.NOTEBOOKLM_URL, wait_until="domcontentloaded", timeout=60000
                )

        try:
            yield context, target_page
        finally:
            logger.info("Closing CDP connection (user Chrome remains running).")
            browser.close()