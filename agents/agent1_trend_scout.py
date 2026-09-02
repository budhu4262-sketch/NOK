import json
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Ensure project root is in sys.path for standalone execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings
from utils.tabi_client import TabiClient

logger = logging.getLogger("agent1_trend_scout")


def run_agent1(custom_niche: Optional[str] = None) -> Dict[str, Any]:
    """Agent 1: Scout 5 viral, counter-intuitive data visualization concepts and choose the top concept."""
    niche = custom_niche or "Data Visualization & Global Statistics"
    logger.info("Agent 1 starting: Scouting viral concepts for niche: %s", niche)

    system_prompt = (
        "You are an elite YouTube data storytelling strategist and viral concept scout. "
        "Your specialty is identifying counter-intuitive, high-retention data shifts and global statistics "
        "that hook viewers immediately with shocking visual contrast."
    )

    user_prompt = f"""Target Niche: {niche}

Generate 5 viral, counter-intuitive YouTube video concepts centered around dynamic data visualization.
Themes can include: wealth distribution shifts, demographic collapse, clean energy transition anomalies, sovereign debt avalanches, global resource tipping points, or unexpected economic divergences.

Each concept must have:
1. "title": High-CTR curiosity title
2. "hook": First 5-second verbal hook that challenges common intuition
3. "core_data_shift": The key statistical anomaly or historical pivot point
4. "visual_concept": Description of how the animated chart/graph creates dramatic contrast
5. "retention_score": Predicted retention score (1 to 100)
6. "rationale": Why this concept will keep viewers watching until the end

Return a JSON object in this exact schema:
{{
  "niche": "{niche}",
  "concepts": [
    {{
      "id": 1,
      "title": "...",
      "hook": "...",
      "core_data_shift": "...",
      "visual_concept": "...",
      "retention_score": 95,
      "rationale": "..."
    }}
  ],
  "selected_concept": {{ ... chosen highest retention concept ... }}
}}
"""

    client = TabiClient()
    result = client.generate_json(user_prompt, system_prompt=system_prompt, temperature=0.7)

    if "selected_concept" not in result and "concepts" in result and result["concepts"]:
        result["selected_concept"] = max(
            result["concepts"], key=lambda x: x.get("retention_score", 0)
        )

    settings.TOPIC_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    logger.info(
        "Agent 1 completed: Selected topic '%s' -> %s",
        result.get("selected_concept", {}).get("title", "Unknown"),
        settings.TOPIC_FILE,
    )
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_agent1()