import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Directory Layout
CONFIG_DIR = PROJECT_ROOT / "config"
WORKSPACE_DIR = PROJECT_ROOT / "workspace"
AGENTS_DIR = PROJECT_ROOT / "agents"
UTILS_DIR = PROJECT_ROOT / "utils"
ASSETS_DIR = PROJECT_ROOT / "assets"
RUNS_DIR = PROJECT_ROOT / "runs"

for directory in [CONFIG_DIR, WORKSPACE_DIR, AGENTS_DIR, UTILS_DIR, ASSETS_DIR, RUNS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Workspace Artifacts
TOPIC_FILE = WORKSPACE_DIR / "01_topic.json"
SOURCE_FILE = WORKSPACE_DIR / "02_source.txt"
VERIFIED_SOURCE_FILE = WORKSPACE_DIR / "03_verified_source.txt"
PROMPTS_FILE = WORKSPACE_DIR / "04_notebook_prompts.json"
RAW_VIDEO_FILE = WORKSPACE_DIR / "06_raw_video.mp4"
TRANSCRIPT_FILE = WORKSPACE_DIR / "07_transcript.json"
OUTRO_FILE = WORKSPACE_DIR / "07_outro.json"
VOICED_VIDEO_FILE = WORKSPACE_DIR / "08_voiced_video.mp4"
FINAL_VIDEO_FILE = WORKSPACE_DIR / "09_final_video.mp4"
METADATA_FILE = WORKSPACE_DIR / "10_metadata.json"
THUMBNAIL_FILE = WORKSPACE_DIR / "11_thumbnail.png"
MANIFEST_FILE = WORKSPACE_DIR / "12_manifest.json"

# TabiAI / Tabitoken LLM Settings
TABI_API_KEY = os.getenv("TABI_API_KEY", "")
TABI_BASE_URL = os.getenv("TABI_BASE_URL", "https://api.tabitoken.com/v1")
TABI_MODEL = os.getenv("TABI_MODEL", "claude-opus-5")

# CDP Settings (NotebookLM Browser Automation)
CDP_URL = os.getenv("CDP_URL", "http://localhost:9222")
NOTEBOOKLM_URL = "https://notebooklm.google.com/"

# Harvester Wait Times (Seconds)
HARVESTER_INITIAL_WAIT_SEC = int(os.getenv("HARVESTER_INITIAL_WAIT_SEC", "1200"))
HARVESTER_POLL_INTERVAL_SEC = int(os.getenv("HARVESTER_POLL_INTERVAL_SEC", "120"))
HARVESTER_TIMEOUT_SEC = int(os.getenv("HARVESTER_TIMEOUT_SEC", "4500"))

# Voice Transformation & Outro Settings
TARGET_VOICE_SAMPLE = ASSETS_DIR / "target_voice.wav"
EDGE_TTS_VOICE = os.getenv("TARGET_VOICE_NAME", "en-US-ChristopherNeural")
SEED_VC_CLI_PATH = os.getenv("SEED_VC_CLI_PATH", "")
RVC_CLI_PATH = os.getenv("RVC_CLI_PATH", "")

# Subtitle (ASS) Configuration
SUBTITLE_STYLE = {
    "Fontname": "Impact",
    "Fontsize": 26,
    "PrimaryColour": "&H00FFFFFF",     # White default text
    "HighlightColour": "&H002EFFFF",   # Neon Gold/Yellow word highlight
    "OutlineColour": "&H00000000",     # Solid black outline
    "BackColour": "&H64000000",        # Translucent drop shadow
    "Bold": 1,
    "Italic": 0,
    "Outline": 2.5,
    "Shadow": 1.5,
    "Alignment": 2,                    # Bottom center
    "MarginV": 50,
}

# Gemini API Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip('"').strip("'")

# YouTube Publishing Settings
YOUTUBE_CLIENT_SECRETS = PROJECT_ROOT / os.getenv("YOUTUBE_CLIENT_SECRETS", "config/client_secrets.json")
YOUTUBE_TOKEN_PATH = CONFIG_DIR / "token.json"
YOUTUBE_PRIVACY_STATUS = os.getenv("YOUTUBE_PRIVACY_STATUS", "private").strip('"')
YOUTUBE_CATEGORY_ID = os.getenv("YOUTUBE_CATEGORY_ID", "28").strip('"')  # 28: Science & Tech, 27: Education
DAILY_VIDEO_LIMIT = int(os.getenv("DAILY_VIDEO_LIMIT", "2").strip('"'))
DAILY_TRACKER_FILE = CONFIG_DIR / "daily_tracker.json"

