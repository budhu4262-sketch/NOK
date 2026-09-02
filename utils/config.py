import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import settings

logger = logging.getLogger("config_manager")


def read_env_file(env_path: Path = PROJECT_ROOT / ".env") -> Dict[str, str]:
    """Reads .env safely into a key-value dictionary without altering files."""
    if not env_path.exists():
        return {}
    env_vars = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k, v = stripped.split("=", 1)
                env_vars[k.strip()] = v.strip().strip('"').strip("'")
    return env_vars


def update_env_file(updates: Dict[str, str], env_path: Path = PROJECT_ROOT / ".env") -> None:
    """Updates or appends keys in .env without wiping or removing existing keys."""
    lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    updated_keys = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, _ = stripped.split("=", 1)
            k = k.strip()
            if k in updates:
                new_lines.append(f'{k}="{updates[k]}"\n')
                updated_keys.add(k)
                continue
        new_lines.append(line)

    for k, v in updates.items():
        if k not in updated_keys:
            new_lines.append(f'{k}="{v}"\n')

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    logger.info("Safely updated .env variables: %s", list(updates.keys()))


def validate_environment() -> Tuple[bool, Dict[str, Any]]:
    """
    Validates critical environment configurations:
    - GEMINI_API_KEY
    - TABI_API_KEY
    - YouTube client secrets and token
    Prints clear terminal alerts for missing items.
    """
    env_vars = read_env_file()
    status = {}
    all_valid = True

    print("\n" + "=" * 65)
    print(" [CONFIG VALIDATION] Checking System Keys & Credentials")
    print("=" * 65)

    # 1. Gemini API Key
    gemini_key = env_vars.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    if gemini_key:
        masked = gemini_key[:8] + "..." + gemini_key[-6:] if len(gemini_key) > 14 else "***"
        print(f"  [OK]       GEMINI_API_KEY: Present ({masked})")
        status["gemini"] = True
    else:
        print("  [ALERT]    GEMINI_API_KEY: MISSING in .env (Thumbnail fallback active)")
        status["gemini"] = False

    # 2. TabiAI (Claude Opus) Key
    tabi_key = env_vars.get("TABI_API_KEY", os.getenv("TABI_API_KEY", ""))
    if tabi_key:
        masked = tabi_key[:8] + "..." + tabi_key[-6:] if len(tabi_key) > 14 else "***"
        print(f"  [OK]       TABI_API_KEY: Present ({masked})")
        status["tabi"] = True
    else:
        print("  [ALERT]    TABI_API_KEY: MISSING in .env (Mock fallback active)")
        status["tabi"] = False

    # 3. YouTube Client Secrets
    secrets_path = settings.YOUTUBE_CLIENT_SECRETS
    if secrets_path.exists() and secrets_path.stat().st_size > 20:
        print(f"  [OK]       YOUTUBE SECRETS: Found at {secrets_path.name}")
        status["youtube_secrets"] = True
    else:
        print(f"  [ALERT]    YOUTUBE SECRETS: Missing at {secrets_path}")
        status["youtube_secrets"] = False
        all_valid = False

    # 4. YouTube OAuth Token (token.json)
    token_path = settings.YOUTUBE_TOKEN_PATH
    if token_path.exists() and token_path.stat().st_size > 20:
        print(f"  [OK]       YOUTUBE TOKEN: Found at {token_path.name} (Live Upload Ready)")
        status["youtube_token"] = True
    else:
        print(f"  [NOTICE]   YOUTUBE TOKEN: Not found at {token_path.name}")
        print("             Run 'python auth_youtube.py' once to link your YouTube channel.")
        status["youtube_token"] = False

    # 5. YouTube Publishing Defaults
    privacy = env_vars.get("YOUTUBE_PRIVACY_STATUS", settings.YOUTUBE_PRIVACY_STATUS)
    category = env_vars.get("YOUTUBE_CATEGORY_ID", settings.YOUTUBE_CATEGORY_ID)
    daily_limit = env_vars.get("DAILY_VIDEO_LIMIT", str(settings.DAILY_VIDEO_LIMIT))
    print(f"  [DEFAULTS] Privacy: {privacy} | Category ID: {category} | Daily Limit: {daily_limit}")
    print("=" * 65 + "\n")

    return all_valid, status


if __name__ == "__main__":
    validate_environment()