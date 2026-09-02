import json
import logging
import sys
from pathlib import Path

# Ensure project root is in sys.path for standalone execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings
from utils.tabi_client import TabiClient

logger = logging.getLogger("agent2_source_writer")


def run_agent2() -> str:
    """Agent 2: Writes a 1,500-word structured document tailored for NotebookLM ingestion."""
    logger.info("Agent 2 starting: Reading topic from %s", settings.TOPIC_FILE)
    if not settings.TOPIC_FILE.exists():
        raise FileNotFoundError(f"Missing topic file: {settings.TOPIC_FILE}. Run Agent 1 first.")

    topic_data = json.loads(settings.TOPIC_FILE.read_text(encoding="utf-8"))
    selected = topic_data.get("selected_concept", {})
    title = selected.get("title", "Global Data Pivot")
    hook = selected.get("hook", "")
    core_data_shift = selected.get("core_data_shift", "")
    visual_concept = selected.get("visual_concept", "")

    system_prompt = (
        "You are an authoritative investigative data journalist and documentary researcher. "
        "You write comprehensive, deeply researched, data-dense source material specifically designed "
        "to be ingested by Google NotebookLM's Cinematic Video Overview engine. "
        "Your writing is packed with exact statistics, chronological milestones, comparative metrics, "
        "and vivid analogies that naturally translate into motion infographics."
    )

    user_prompt = f"""Topic Title: {title}
Core Hook: {hook}
Key Data Pivot: {core_data_shift}
Visual Style Guidance: {visual_concept}

Write an exhaustive, 1,500-word source dossier tailored for NotebookLM.
Structure the document rigorously with clear Markdown headings:
# {title}: The Hidden Statistical Reality

## Section 1: The Intuition Trap (The False Consensus)
- Detail what 90% of the public believes to be true.
- Contrast with the real data curve over the past 50 years.
- Include precise percentages, year-over-year deltas, and baseline numbers.

## Section 2: The Anatomy of the Pivot (Chronological Breakdown)
- Milestone-by-milestone breakdown (e.g. 1980, 2000, 2015, 2024, 2035 projections).
- Key triggers: policy shifts, technological disruptions, capital flows, demographic inflection points.
- Include dense bullet points of exact metrics, ratios, and cross-country comparisons.

## Section 3: The Divergence (Winners, Losers, and Outliers)
- Contrast the top 1% vs bottom 50%, or leading nations vs lagging nations.
- Use concrete financial/physical analogies (e.g. "equivalent to the entire GDP of...", "enough energy to power...").
- Highlight the single most staggering statistical outlier that defies standard models.

## Section 4: The 2030 Horizon & Cascading Consequences
- Mathematical projections for the next 5-10 years.
- Second-order and third-order ripple effects across global trade, social contracts, and everyday life.
- The irreversible tipping point metric.

## Section 5: Summary Infographic Data Sheet
- A concise bulleted table of all key data pairs (Year, Metric, Value, Significance) for NotebookLM's visual engine to parse into animated charts.

Maintain an objective, fast-paced, intellectually gripping tone throughout. Ensure dense factual substance.
"""

    client = TabiClient()
    source_text = client.generate(
        user_prompt, system_prompt=system_prompt, temperature=0.6, max_tokens=4096
    )

    settings.SOURCE_FILE.write_text(source_text, encoding="utf-8")
    word_count = len(source_text.split())
    logger.info("Agent 2 completed: Generated %d words -> %s", word_count, settings.SOURCE_FILE)
    return source_text


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_agent2()