import sys
import json
import os
import re
from pathlib import Path
import httpx

# Ensure root folder is accessible for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.config import get_tabi_api_key

WORKSPACE = Path("workspace")

def run_agent10():
    print("[Agent 10] Initializing Elite Packaging Specialist & Viral Strategist...")
    WORKSPACE.mkdir(parents=True, exist_ok=True)

    transcript_path = WORKSPACE / "07_transcript.json"
    topic_path = WORKSPACE / "01_topic.json"

    transcript_text = ""
    if transcript_path.exists():
        try:
            with open(transcript_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    transcript_text = " ".join([seg.get("text", "") for seg in data[:40]])
                elif isinstance(data, dict):
                    transcript_text = data.get("full_text", "")[:3000]
        except Exception as e:
            print(f"[Agent 10 Warning] Could not parse transcript: {e}")

    topic_context = "Demographic and Economic Crisis"
    if topic_path.exists():
        try:
            with open(topic_path, "r", encoding="utf-8") as f:
                topic_context = json.load(f).get("topic", topic_context)
        except Exception:
            pass

    system_instruction = (
        "You are an elite YouTube growth strategist and packaging director for documentary channels "
        "like Fern, Magnates Media, Vox, and Johnny Harris. You engineer viral, curiosity-inducing "
        "titles and descriptions with an obsession for high CTR and long session duration.\n\n"
        "STRICT TITLE FORMULAS (< 50 characters, choose the highest psychological tension):\n"
        "- The Point of No Return: e.g., 'South Korea Is Quietly Disappearing'\n"
        "- The Dangerous Number: e.g., 'The Number That Erases a Country'\n"
        "- The Paradox: e.g., 'Why Korea Has No Future'\n"
        "RULES FOR TITLES:\n"
        "1. Max 48 characters total.\n"
        "2. FORBIDDEN words: 'Explained', 'Documentary', 'Analysis', 'Deep Dive', 'Case Study', 'The Math Of'.\n"
        "3. High contrast, visceral, irreversible tension.\n\n"
        "STRICT DESCRIPTION ARCHITECTURE:\n"
        "- Line 1-2 (Crucial: Above 'Show More' fold): A gut-punch hook stating the irreversible reality.\n"
        "- Key Insights: 3 bullet points highlighting the shocking facts extracted directly from the context.\n"
        "- Natural SEO paragraph embedding high-volume search keywords seamlessly without keyword stuffing.\n"
        "- 3 ultra-targeted hashtags.\n\n"
        "TAGS ARCHITECTURE:\n"
        "- Exactly 15 long-tail, high-intent search phrases (e.g., 'South Korea demographic cliff', "
        "'fertility rate 0.72 explained', 'why South Korea population is collapsing', 'extinction rate Asia').\n\n"
        "Return ONLY a clean JSON object with exact keys: 'primary_title', 'ab_titles' (list of 3 alternatives), "
        "'description', 'tags' (list of 15 strings), 'category_id' (must be '28')."
    )

    user_prompt = (
        f"Topic Focus: {topic_context}\n\n"
        f"Script Transcript Excerpt:\n{transcript_text if transcript_text else 'South Korea fertility rate dropped to record low 0.72, schools shutting down, demographic cliff, economic irreversible decline.'}\n\n"
        "Generate elite packaging now:"
    )

    api_key = get_tabi_api_key() or os.getenv("TABI_API_KEY")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.65,
        "max_tokens": 1200
    }

    meta = None
    try:
        print("[Agent 10] Querying Claude 3.5 Sonnet for deep viral packaging research...")
        response = httpx.post("https://tabitoken.com/v1/chat/completions", headers=headers, json=payload, timeout=60.0)
        res_json = response.json()
        raw_content = res_json["choices"][0]["message"]["content"]

        # Parse JSON
        match = re.search(r"\{.*\}", raw_content, re.DOTALL)
        if match:
            meta = json.loads(match.group(0))
        else:
            meta = json.loads(raw_content)

    except Exception as e:
        print(f"[Agent 10 Notice] Model formatting error ({e}), applying hand-crafted elite documentary preset.")
        meta = {
            "primary_title": "South Korea Is Quietly Disappearing",
            "ab_titles": [
                "The Number That Deletes a Country",
                "0.72: The Point of No Return",
                "Why Nobody Wants Children Here"
            ],
            "description": (
                "South Korea's fertility rate has crossed an irreversible mathematical threshold that no modern civilization has ever survived.\n\n"
                "• At a 0.72 birth rate, every incoming generation shrinks by more than 60%\n"
                "• Primary schools, pediatric clinics, and entire townships are quietly being shuttered\n"
                "• The world's fastest aging economy is entering a compounding demographic trap\n\n"
                "A forensic breakdown of the economic and social pressures fueling the world's most severe population cliff.\n\n"
                "#SouthKorea #Demographics #Economics"
            ),
            "tags": [
                "South Korea demographic crisis", "fertility rate collapse", "South Korea population cliff",
                "why South Korea is shrinking", "demographic decline documentary", "0.72 birth rate crisis",
                "South Korea economy collapse", "Asia population crisis", "South Korea extinction",
                "empty schools South Korea", "Seoul housing crisis fertility", "global demographic winter",
                "economic consequences low birth rate", "population collapse explained", "future of South Korea"
            ],
            "category_id": "28"
        }

    # Strict Sanitation
    meta["category_id"] = "28"
    if len(meta.get("primary_title", "")) > 50:
        meta["primary_title"] = meta["primary_title"][:47].strip() + "..."

    output_path = WORKSPACE / "10_metadata.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print("\n" + "="*50)
    print(f"🔥 PRIMARY VIRAL TITLE: {meta['primary_title']}")
    print(f"📌 A/B TESTING TITLES : {meta.get('ab_titles', [])}")
    print(f"🏷️ TOTAL TAGS          : {len(meta.get('tags', []))} targeted tags")
    print(f"📄 METADATA SAVED TO   : {output_path}")
    print("="*50 + "\n")

    return meta

if __name__ == "__main__":
    run_agent10()