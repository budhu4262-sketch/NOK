import os
from pathlib import Path
from dotenv import load_dotenv

# Load local .env if available
load_dotenv()

def get_env_var(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()

def get_tabi_api_key() -> str:
    """Fetches Claude/Anthropic/Tabi API key from environment."""
    return (
        os.environ.get("TABI_API_KEY") or
        os.environ.get("ANTHROPIC_API_KEY") or
        os.environ.get("CLAUDE_API_KEY") or
        ""
    ).strip()

def get_gemini_api_key() -> str:
    """Fetches Google Gemini API key from environment."""
    return (
        os.environ.get("GEMINI_API_KEY") or
        os.environ.get("GOOGLE_API_KEY") or
        ""
    ).strip()

def get_youtube_credentials_path() -> Path:
    return Path("token.json")

def get_client_secrets_path() -> Path:
    return Path("client_secrets.json")