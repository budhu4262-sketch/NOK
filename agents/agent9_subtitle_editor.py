import json
import logging
import subprocess
import sys
from pathlib import Path

# Ensure project root is in sys.path for standalone execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import settings

logger = logging.getLogger("agent9_subtitle_editor")


def format_ass_time(seconds: float) -> str:
    """Formats seconds to ASS timestamp format: H:MM:SS.cs (centiseconds)."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        centis = 99
    return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"


def build_ass_content(transcript: dict) -> str:
    """
    Generates an Advanced SubStation Alpha (.ass) subtitle file with
    bold modern typography, stroke outline, shadow, and dynamic word-by-word highlights.
    """
    style = settings.SUBTITLE_STYLE

    ass_header = f"""[Script Info]
Title: Dynamic Data Viz Word-Highlight Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: None
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style['Fontname']},{style['Fontsize'] * 2},{style['PrimaryColour']},{style['HighlightColour']},{style['OutlineColour']},{style['BackColour']},{style['Bold']},{style['Italic']},0,0,100,100,0,0,1,{style['Outline'] * 2},{style['Shadow'] * 2},{style['Alignment']},20,20,{style['MarginV'] * 2},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    dialogues = []
    words = transcript.get("words", [])

    if not words and transcript.get("segments"):
        # Fallback to segment-level subtitles
        for seg in transcript["segments"]:
            start_str = format_ass_time(seg["start"])
            end_str = format_ass_time(seg["end"])
            txt = seg["text"].replace("\n", " ").strip()
            dialogues.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{txt}")
    else:
        # Group words into short dynamic chunks (3 to 5 words per subtitle card)
        chunk_size = 4
        for i in range(0, len(words), chunk_size):
            chunk = words[i : i + chunk_size]
            if not chunk:
                continue

            for active_idx, target_word in enumerate(chunk):
                w_start = target_word["start"]
                w_end = target_word["end"]
                if w_end <= w_start:
                    w_end = w_start + 0.35

                start_str = format_ass_time(w_start)
                end_str = format_ass_time(w_end)

                # Format the card: active word in HighlightColour, other words in PrimaryColour
                card_tokens = []
                for idx, w in enumerate(chunk):
                    raw_w = w["word"].upper()
                    if idx == active_idx:
                        # Highlight active word with gold/neon color
                        card_tokens.append(f"{{\\c{style['HighlightColour']}}}{raw_w}{{\\c{style['PrimaryColour']}}}")
                    else:
                        card_tokens.append(raw_w)

                card_text = " ".join(card_tokens)
                dialogues.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{card_text}")

    return ass_header + "\n".join(dialogues) + "\n"


def run_agent9() -> Path:
    """
    Agent 9: Subtitle & Dynamic Editor.
    Parses word timestamps, builds animated ASS subtitle track,
    and burns into workspace/09_final_video.mp4 without re-encoding audio.
    """
    logger.info("Agent 9 starting: Subtitle & Dynamic Editor")

    input_video = settings.VOICED_VIDEO_FILE
    if not input_video.exists():
        if settings.RAW_VIDEO_FILE.exists():
            logger.warning("Voiced video not found. Using raw video as fallback input.")
            input_video = settings.RAW_VIDEO_FILE
        else:
            raise FileNotFoundError("Missing voiced video or raw video input. Run Agent 8 first.")

    if not settings.TRANSCRIPT_FILE.exists():
        raise FileNotFoundError(f"Missing transcript: {settings.TRANSCRIPT_FILE}. Run Agent 7 first.")

    transcript = json.loads(settings.TRANSCRIPT_FILE.read_text(encoding="utf-8"))

    # 1. Generate ASS Subtitle file
    ass_path = settings.WORKSPACE_DIR / "09_subtitles.ass"
    ass_content = build_ass_content(transcript)
    ass_path.write_text(ass_content, encoding="utf-8")
    logger.info("ASS Subtitles generated -> %s", ass_path)

    # 2. Burn subtitles via FFmpeg with libass without re-encoding audio (-c:a copy)
    # On Windows, libass filter needs escaped colon or forward slashes
    escaped_ass = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:")

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_video),
        "-vf",
        f"ass='{escaped_ass}'",
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-preset",
        "fast",
        "-c:a",
        "copy",
        str(settings.FINAL_VIDEO_FILE),
    ]

    logger.info("Burning subtitles via FFmpeg libass into final video...")
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as err:
        logger.error("FFmpeg ASS burning failed: %s", err.stderr.decode("utf-8", errors="ignore"))
        # Fallback: copy video without burning subtitles if font/filter fails
        logger.warning("Copying video as final output fallback without subtitle burn.")
        import shutil
        shutil.copyfile(input_video, settings.FINAL_VIDEO_FILE)

    file_size_mb = settings.FINAL_VIDEO_FILE.stat().st_size / (1024 * 1024)
    logger.info("Agent 9 completed: Final video ready (%0.2f MB) -> %s", file_size_mb, settings.FINAL_VIDEO_FILE)
    return settings.FINAL_VIDEO_FILE


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_agent9()