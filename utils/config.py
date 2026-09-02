import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def get_env_var(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()

def get_tabi_api_key() -> str:
    return (
        os.environ.get("TABI_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("CLAUDE_API_KEY")
        or ""
    ).strip()

def get_gemini_api_key() -> str:
    return (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or ""
    ).strip()

def get_youtube_credentials_path() -> Path:
    return Path("token.json")

def get_client_secrets_path() -> Path:
    return Path("client_secrets.json")

def validate_environment() -> bool:
    """Validates that essential keys or files exist."""
    print("[Config] Checking runner environment variables...")
    has_gemini = bool(get_gemini_api_key())
    has_tabi = bool(get_tabi_api_key())
    has_token = Path("token.json").exists()
    has_secrets = Path("client_secrets.json").exists()

    print(f" - Gemini API Key: {'Available' if has_gemini else 'Missing'}")
    print(f" - Tabi/Claude API Key: {'Available' if has_tabi else 'Missing'}")
    print(f" - YouTube Token: {'Available' if has_token else 'Missing'}")
    print(f" - Client Secrets: {'Available' if has_secrets else 'Missing'}")

    return True