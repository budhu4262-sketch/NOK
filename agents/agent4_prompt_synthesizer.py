import json
import logging
import sys
from pathlib import Path

# Ensure project root is in sys.path for standalone execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings
from utils.tabi_client import TabiClient

logger = logging.getLogger("agent4_prompt_synthesizer")

# Locked visual prompt across all videos for visual consistency in the niche
LOCKED_VISUAL_PROMPT = (
    "Minimalist 2D data visualization aesthetic, clean flat vector graphics, "
    "high-contrast palette, dynamic infographic motion, zero clutter, zero 3D artifacts."
)


def run_agent4() -> dict:
    """Agent 4: Synthesizes locked visual prompt and dynamic steering prompt for NotebookLM."""
    logger.info("Agent 4 starting: Reading verified source from %s", settings.VERIFIED_SOURCE_FILE)
    if not settings.VERIFIED_SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Missing verified source: {settings.VERIFIED_SOURCE_FILE}. Run Agent 3 first."
        )

    verified_text = settings.VERIFIED_SOURCE_FILE.read_text(encoding="utf-8")

    system_prompt = (
        "You are a cinematic director for AI-generated data documentary overviews. "
        "You craft concise, highly directive steering prompts that dictate the pacing, "
        "visual scene transitions, narrative arc, and tone of NotebookLM Cinematic Video Overviews."
    )

    user_prompt = f"""Based on the following verified source document, generate a dynamic Steering Prompt for NotebookLM Cinematic Video Overview.

Source Summary (First 1500 chars):
{verified_text[:1500]}

Guidelines for Steering Prompt:
- Pacing: Fast, energetic, documentary-style build-up from intuition trap to final tipping point.
- Scene Guidance: Direct the visual engine to focus on dynamic bar charts, comparative area graphs, and animated timelines.
- Tone: Gripping, data-driven, urgent yet objective.
- Length: Exactly 2-4 dense sentences (under 75 words).

Return a JSON object in this exact schema:
{{
  "locked_visual_prompt": "{LOCKED_VISUAL_PROMPT}",
  "steering_prompt": "...",
  "combined_custom_instructions": "..."
}}
"""

    client = TabiClient()
    result = client.generate_json(user_prompt, system_prompt=system_prompt, temperature=0.5)

    # Ensure locked visual prompt is strictly preserved
    result["locked_visual_prompt"] = LOCKED_VISUAL_PROMPT
    steering = result.get(
        "steering_prompt",
        "Focus on dynamic infographic transitions, high contrast graphs, and chronological data curves.",
    )
    result["combined_custom_instructions"] = f"{LOCKED_VISUAL_PROMPT} | Steering: {steering}"

    settings.PROMPTS_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    logger.info("Agent 4 completed: Prompts synthesized -> %s", settings.PROMPTS_FILE)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_agent4()