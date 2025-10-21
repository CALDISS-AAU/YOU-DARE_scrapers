#!/bin/bash
set -euo pipefail
pip3 install -U yt-dlp jq

# === CONFIGURATION ===
URLS_FILE="/work/YOU-DARE/scrapers/scrapers/spiders/Spain/yt-dlp/all_urls.txt"  # list of video URLs
OUTPUT_DIR="/work/YOU-DARE/scrapers/data/Spain/vox_espana_YT/"
COOKIES="/work/YOU-DARE/scrapers/scrapers/functions/cookies_2.txt"
FFMPEG_DIR="/work/YOU-DARE/scrapers/ffmpeg-7.0.2-amd64-static"
SOURCE_NAME="vox_españa"
JL_FILE="$OUTPUT_DIR/metadata.jl"

# === TOKEN SETUP & SANITIZATION ===
TOKEN_URL='Ml94M8WVTtcqEHgPN2pZj0SeDufsjUxgv3dezux-zD-8zeDPwKBqLQeXJPlUDCqxghWU2h1lAPUd9Rd0u-WnluOhJN2YS_TEjQw12CkPAg5HrFpwVxFKM2Ba--i1sbt4yg=='
TOKEN_URL="$(printf '%s' "$TOKEN_URL" | tr -d '\r\n ' | LC_ALL=C tr -cd 'A-Za-z0-9_-')"
printf '%s' "$TOKEN_URL" | od -An -t x1 | tr -d ' \n' ; echo
LC_ALL=C grep -q '^[A-Za-z0-9_-]\+$' <<<"$TOKEN_URL" && echo OK || echo BAD

# === SETUP ===
mkdir -p "$OUTPUT_DIR"
DOWNLOAD_DATE=$(date +%Y-%m-%d)
> "$JL_FILE"

# === PROCESS ===
yt-dlp \
  --skip-download \
  --print-json \
  --ignore-errors \
  --ffmpeg-location "$FFMPEG_DIR" \
  --cookies "$COOKIES" \
  --extractor-args "youtube:po_token=web.gvs+$TOKEN_URL;player_client=mweb" \
  -a "$URLS_FILE" \
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