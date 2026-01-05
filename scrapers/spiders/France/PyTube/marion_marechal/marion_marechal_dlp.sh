#!/bin/bash
set -euo pipefail
pip3 install -U yt-dlp jq

# === CONFIGURATION ===
URL='https://www.youtube.com/@MarionMarechalOfficiel/videos'
OUTPUT_DIR="/work/YOU-DARE/scrapers/data/France/marion_marechal_dlp"
ARCHIVE_FILE="$OUTPUT_DIR/archive.txt"
COOKIES="/work/YOU-DARE/scrapers/scrapers/functions/cookies.txt"
SOURCE_NAME="@MarionMarechalOfficiel"
JL_FILE="$OUTPUT_DIR/metadata.jl"

# === SETUP ===
mkdir -p "$OUTPUT_DIR"
DOWNLOAD_DATE=$(date +%Y-%m-%d)
> "$JL_FILE"

# === PROCESS (METADATA ONLY) ===
yt-dlp "$URL" \
  --skip-download \
  --download-archive "$ARCHIVE_FILE" \
  --cookies "$COOKIES" \
  --extractor-args "youtubepot-bgutilhttp:base_url=http://[::1]:4416;player_client=mweb" \
  --sleep-interval 4.5 \
  --max-sleep-interval 9 \
  --retries 10 \
  --extractor-retries 3 \
  --socket-timeout 15 \
  --ignore-errors \
  --ignore-no-formats-error \
  --no-progress \
  --print-json 2>"$OUTPUT_DIR/yt-dlp.log" \
| jq -rc --arg dl "$DOWNLOAD_DATE" --arg src "$SOURCE_NAME" '
    select(.id and .webpage_url) |
    {
      video_id: .id,
      video_title: .title,
      video_link: .webpage_url,
      publication_date: .upload_date,
      scrape_date: $dl,
      source: $src
    }
' >> "$JL_FILE" || true

echo "✅ Metadata exported to $JL_FILE"