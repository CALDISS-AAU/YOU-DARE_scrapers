import json

# --- File paths ---
pytube_metadata_path = '/work/YOU-DARE/scrapers/data/Hungary/fidesz_videos_YT/videos.jl'
ytdlp_metadata_path = '/work/YOU-DARE/scrapers/data/Hungary/fidesz_YT/metadata.jl'
combined_metadata_path = '/work/YOU-DARE/scrapers/data/Hungary/fidesz_videos_YT/combined_metadata.jl'

# --- Step 1: read both JSONL files and collect unique entries by video_id ---
unique_data = {}

for path in [pytube_metadata_path, ytdlp_metadata_path]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                item = json.loads(line)
                vid = item.get("video_id")
                if vid and vid not in unique_data:
                    unique_data[vid] = item
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON line in {path}: {line.strip()}")

# --- Step 2: write combined results ---
with open(combined_metadata_path, "w", encoding="utf-8") as out:
    for item in unique_data.values():
        out.write(json.dumps(item, ensure_ascii=False) + "\n")

# --- Step 3: summary ---
print(f"Merged files:")
print(f" - {pytube_metadata_path}")
print(f" - {ytdlp_metadata_path}")
print(f"Saved combined file to: {combined_metadata_path}")
print(f"Total unique entries (by video_id): {len(unique_data)}")
