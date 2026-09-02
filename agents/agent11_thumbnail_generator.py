import os
import shutil
from pathlib import Path

WORKSPACE = Path("workspace")
MANUAL_CUSTOM = WORKSPACE / "custom_thumbnail.png"
FINAL_THUMBNAIL = WORKSPACE / "11_thumbnail.png"

def run_agent11():
    print("[Agent 11] Thumbnail Handler: Manual Mode Active")
    WORKSPACE.mkdir(parents=True, exist_ok=True)

    # 1. Check if user dropped a custom thumbnail
    if MANUAL_CUSTOM.exists():
        print(f"[Agent 11] Custom thumbnail found at {MANUAL_CUSTOM}. Syncing to pipeline output...")
        shutil.copyfile(MANUAL_CUSTOM, FINAL_THUMBNAIL)
        print(f"[Agent 11 Success] Locked {FINAL_THUMBNAIL} for publishing.")
        return FINAL_THUMBNAIL

    # 2. Check if 11_thumbnail.png already exists (user dropped it directly)
    if FINAL_THUMBNAIL.exists() and FINAL_THUMBNAIL.stat().st_size > 5000:
        print(f"[Agent 11] Using existing {FINAL_THUMBNAIL}.")
        return FINAL_THUMBNAIL

    print("[Agent 11 Notice] No custom thumbnail found in workspace yet.")
    print("Drop your thumbnail as: workspace/custom_thumbnail.png or workspace/11_thumbnail.png")
    return FINAL_THUMBNAIL

if __name__ == "__main__":
    run_agent11()