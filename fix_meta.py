import json
import subprocess
import os
from pathlib import Path

workspace = Path("workspace")
raw_video = workspace / "06_raw_video.mp4"

print("[1/3] Extracting clean audio from 93MB video...")
subprocess.run([
    "ffmpeg", "-y", "-i", str(raw_video),
    "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
    str(workspace / "07_clean_audio.wav")
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

print("[2/3] Setting accurate South Korea metadata in 10_metadata.json...")
meta = {
    "title": "The Compounding Cliff: South Korea's Population Math Explained",
    "description": "An analytical documentary exploring the mathematical reality of South Korea's demographic cliff, fertility rate trajectories, and economic implications.\n\nData and analysis powered by autonomous research models.\n\n#SouthKorea #Demographics #Economics #Documentary",
    "tags": ["South Korea", "demographic crisis", "population collapse", "fertility rate", "economics", "documentary", "data analysis"],
    "category_id": "28",
    "thumbnail_hook": "South Korea 0.72 Fertility Rate Demographic Collapse",
    "thumbnail_visual": "Cinematic 16:9 documentary graphic showing neon red declining population curves over a dark Seoul skyline at night with glowing demographic data."
}
with open(workspace / "10_metadata.json", "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2)

with open(workspace / "01_topic.json", "w", encoding="utf-8") as f:
    json.dump({"topic": "South Korea Population Math and Demographic Cliff", "domain": "Economics & Demographics"}, f, indent=2)

print("[3/3] Done! Metadata and Topic aligned with actual video.")