#!/bin/bash
set -euo pipefail
pip3 install -U yt-dlp jq

# === CONFIGURATION ===
URL="https://www.youtube.com/@fidesz_hu/videos"
OUTPUT_DIR="/work/YOU-DARE/scrapers/data/Hungary/fidesz_YT"
ARCHIVE_FILE="/work/YOU-DARE/scrapers/data/Hungary/fidesz_YT/archive.txt"
AUDIO_OUTPUT_DIR="/work/YOU-DARE/scrapers/data/Hungary/fidesz_YT/m4a_files"
# COOKIES="/work/YOU-DARE/scrapers/scrapers/functions/coockies.txt"
FFMPEG_DIR="/work/YOU-DARE/scrapers/ffmpeg-7.0.2-amd64-static"
SOURCE_NAME="Fidesz"
JL_FILE="$OUTPUT_DIR/metadata.jl"

# === SETUP ===
mkdir -p "$OUTPUT_DIR" "$AUDIO_OUTPUT_DIR"
DOWNLOAD_DATE=$(date +%Y-%m-%d)
> "$JL_FILE"
# --format "ba[ext=m4a]/ba[acodec^=opus]/ba/best"
# === PROCESS ===
yt-dlp "$URL" \
  --skip-download \
  --print-json \
  --ignore-errors \
  --ffmpeg-location "$FFMPEG_DIR" \
  --cookies-from-browser firefox \
  --extractor-args "youtubepot-bgutilhttp:base_url=http://[::1]:41891;player_client=mweb" \
  -a "/work/YOU-DARE/scrapers/data/Hungary/fidesz_YT/metadata.jl" \
| jq -rc --arg dl "$DOWNLOAD_DATE" --arg src "$SOURCE_NAME" '
    # Keep only real video entries with ids
    select(.id and .webpage_url) |
    {
      video_id: .id,
      video_title: .title,
      video_link: .webpage_url,
      publication_date: .upload_date,
      scrape_date: $dl,
      source: $src
    }
' >> "$JL_FILE"