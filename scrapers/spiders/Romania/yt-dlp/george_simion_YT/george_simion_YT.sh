#!/bin/bash
set -euo pipefail
pip3 install -U yt-dlp jq

# === CONFIGURATION ===
OUTPUT_DIR="/work/YOU-DARE/scrapers/data/Romania/george_simion_YT"
ARCHIVE_FILE="/work/YOU-DARE/scrapers/data/Romania/george_simion_YT/archive.txt"
AUDIO_OUTPUT_DIR="/work/YOU-DARE/scrapers/data/Romania/george_simion_YT/m4a_files"
COOKIES="/work/YOU-DARE/scrapers/scrapers/functions/cookies(1).txt"
FFMPEG_DIR="/work/YOU-DARE/scrapers/ffmpeg-7.0.2-amd64-static"
SOURCE_NAME="George Simion"
JL_FILE="$OUTPUT_DIR/metadata.jl"

# === TOKEN SETUP & SANITIZATION ===
TOKEN_URL='Ml-hctFQdJMMG6FOaO6TptdkBQxuAdZe6AR_ZfFVPWCxiabQ3NTqaKXITgnD_TqqgFpbxSKJhs3B_68NMBEQULFGdZ2Q4dXTMXTTiLWTa3aj7EC4Ch_tSwVq3Sy75C4-aQ=='
TOKEN_URL="$(printf '%s' "$TOKEN_URL" | tr -d '\r\n ' | LC_ALL=C tr -cd 'A-Za-z0-9_-')"
printf '%s' "$TOKEN_URL" | od -An -t x1 | tr -d ' \n' ; echo
LC_ALL=C grep -q '^[A-Za-z0-9_-]\+$' <<<"$TOKEN_URL" && echo OK || echo BAD

# === SETUP ===
mkdir -p "$OUTPUT_DIR" "$AUDIO_OUTPUT_DIR"
DOWNLOAD_DATE=$(date +%Y-%m-%d)
> "$JL_FILE"

# === PROCESS ===
yt-dlp \
  --download-archive "$ARCHIVE_FILE" \
  --cookies "$COOKIES" \
  --ffmpeg-location "$FFMPEG_DIR" \
  --extractor-args "youtube:po_token=web.gvs+$TOKEN_URL;player_client=mweb" \
  --format "ba[ext=m4a]/ba[acodec^=opus]/ba/best" \
  --audio-format m4a \
  --audio-quality 0 \
  --extract-audio \
  --add-metadata \
  --output "$AUDIO_OUTPUT_DIR/%(id)s.%(ext)s" \
  --sleep-interval 4.5 \
  --max-sleep-interval 10 \
  --retries 10 --extractor-retries 3 --socket-timeout 15 \
  --ignore-errors \
  --ignore-errors --ignore-no-formats-error \
  --no-progress --print-json 2>"$OUTPUT_DIR/yt-dlp.log" \
  -a "/work/YOU-DARE/scrapers/scrapers/spiders/Romania/yt-dlp/george_simion_YT/links.txt" \
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
echo "☑️ Videos exported to $OUTPUT_DIR"
echo "✅ Metadata exported to $JL_FILE"