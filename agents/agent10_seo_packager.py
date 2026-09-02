import os
import json
from pathlib import Path

try:
    from utils.config import get_tabi_api_key
except ImportError:
    def get_tabi_api_key():
        return (
            os.environ.get("TABI_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
            or ""
        ).strip()

def run_agent10(topic_dict: dict, transcript_text: str = "", output_dir: Path = None) -> dict:
    if output_dir is None:
        output_dir = Path("workspace")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / "10_metadata.json"

    topic_title = topic_dict.get("title", topic_dict.get("topic", "Data Shift"))
    api_key = get_tabi_api_key()

    metadata = {
        "title": f"{topic_title} - The Untold Story",
        "description": (
            f"An in-depth breakdown covering {topic_title}.\n\n"
            "Subscribe for more visual stories.\n\n"
            "#Documentary #Analysis #DeepDive"
        ),
        "tags": ["documentary", "deep dive", "analysis", "case study", "untold story"],
        "category_id": "27",
        "privacy_status": "public"
    }

    out_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"[Agent 10] Metadata packaging created at {out_file}")
    return metadata

if __name__ == "__main__":
    sample_topic = {"title": "The Global Wealth Inversion"}
    run_agent10(sample_topic)