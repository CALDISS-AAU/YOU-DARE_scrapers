#!/usr/bin/env python3
# version: 2025-10-14

import json, sys
from pathlib import Path

JL_PATH = Path("/work/YOU-DARE/scrapers/data/Hungary/fidesz_YT/videos.jl")
AUDIO_DIR = Path("/work/YOU-DARE/scrapers/data/Hungary/fidesz_YT/m4a_files_TEMP")

def load_valid_ids(jl_path):
    valid = set()
    with jl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            vid = obj.get("video_id")
            if vid:
                valid.add(f"{vid}.m4a")
    return valid

def main():
    if not JL_PATH.exists():
        print(f"ERROR: JSONL file not found: {JL_PATH}", file=sys.stderr)
        sys.exit(1)
    if not AUDIO_DIR.exists():
        print(f"ERROR: Audio folder not found: {AUDIO_DIR}", file=sys.stderr)
        sys.exit(1)

    valid_filenames = load_valid_ids(JL_PATH)

    deletions = 0
    for p in AUDIO_DIR.glob("*.m4a"):
        if p.name not in valid_filenames:
            try:
                p.unlink()
                deletions += 1
            except Exception as e:
                print(f"Failed to delete {p}: {e}", file=sys.stderr)

    remaining = sum(1 for _ in AUDIO_DIR.glob("*.m4a"))
    print(f"Deleted files: {deletions}")
    print(f"Remaining .m4a files in {AUDIO_DIR}: {remaining}")

if __name__ == "__main__":
    main()
