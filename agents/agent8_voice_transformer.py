import os
import json
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("agent8_voice_transformer")

def run_agent8(dry_run: bool = False):
    workspace = Path("workspace")
    raw_video = workspace / "06_raw_video.mp4"
    voiced_video = workspace / "08_voiced_video.mp4"

    if not raw_video.exists():
        raise FileNotFoundError(f"Raw video missing: {raw_video}")

    logger.info("Agent 8 starting: Deep Documentary Voice Shift")

    if dry_run:
        logger.info("[DRY RUN] Simulating voice transformation...")
        return

    temp_raw = workspace / "temp_raw.wav"
    temp_shifted = workspace / "temp_shifted.wav"

    # 1. Raw video se original audio extract karo
    logger.info("Extracting audio from raw video...")
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw_video),
        "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
        str(temp_raw)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # 2. Deep Documentary Narrator Filter (Noticeable 10% Pitch Drop + Warm Bass Boost)
    logger.info("Applying deep documentary voice shift...")
    voice_filter = (
        "asetrate=44100*0.89,"
        "atempo=1/0.89,"
        "equalizer=f=120:width_type=h:width=80:g=6,"
        "equalizer=f=3200:width_type=h:width=1000:g=2"
    )
    subprocess.run([
        "ffmpeg", "-y", "-i", str(temp_raw),
        "-af", voice_filter,
        "-ar", "44100", "-ac", "2",
        str(temp_shifted)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # 3. Transformed voice ko video ke sath sync mux karo
    logger.info("Muxing deep voiced audio into video...")
    subprocess.run([
        "ffmpeg", "-y", "-i", str(raw_video), "-i", str(temp_shifted),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-map", "0:v:0", "-map", "1:a:0",
        "-shortest",
        str(voiced_video)
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # Cleanup temp files
    for t in [temp_raw, temp_shifted]:
        if t.exists():
            try:
                t.unlink()
            except Exception:
                pass

    logger.info(f"Agent 8 completed: Voiced video created -> {voiced_video}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_agent8()
