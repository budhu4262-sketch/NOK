import logging
import sys
from pathlib import Path

# Ensure project root is in sys.path for standalone execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings
from utils.tabi_client import TabiClient

logger = logging.getLogger("agent3_fact_verifier")


def run_agent3() -> str:
    """Agent 3: Audits source text for logical fallacies, formatting traps, and NotebookLM ingestion density."""
    logger.info("Agent 3 starting: Verifying source text from %s", settings.SOURCE_FILE)
    if not settings.SOURCE_FILE.exists():
        raise FileNotFoundError(f"Missing source file: {settings.SOURCE_FILE}. Run Agent 2 first.")

    source_text = settings.SOURCE_FILE.read_text(encoding="utf-8")

    system_prompt = (
        "You are an expert fact-checker, statistical auditor, and AI ingestion engineer. "
        "Your job is to audit and optimize source documents for Google NotebookLM. "
        "You eliminate ambiguity, ensure numbers are internally consistent, format data points into "
        "unambiguous comparative bullet points, remove conversational fluff, and ensure clear hierarchical headers."
    )

    user_prompt = f"""Audit and enhance the following source text for optimal NotebookLM ingestion.

Tasks:
1. Verify internal statistical consistency, dates, and logical coherence.
2. Ensure every section has strong Markdown headers (`##`) and bullet-pointed data comparisons.
3. Clean up any formatting traps or ambiguous phrasing that could confuse the video overview generator.
4. Keep the output as a clean, polished Markdown document ready for direct upload into NotebookLM.

Source Text:
{source_text}

Return ONLY the verified, optimized Markdown source text without preamble.
"""

    client = TabiClient()
    verified_text = client.generate(
        user_prompt, system_prompt=system_prompt, temperature=0.2, max_tokens=4096
    )

    settings.VERIFIED_SOURCE_FILE.write_text(verified_text, encoding="utf-8")
    logger.info("Agent 3 completed: Verified source saved -> %s", settings.VERIFIED_SOURCE_FILE)
    return verified_text


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_agent3()