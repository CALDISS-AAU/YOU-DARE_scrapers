#!/bin/bash
set -euo pipefail
pip3 install -U yt-dlp jq

# === CONFIGURATION ===
URL="https://www.youtube.com/c/Riksstudios/videos"
ROOT="/work/YOU-DARE/scrapers/data/Sweden/riks_tv_YT"
ARCHIVE="$ROOT/archive.txt"
OUTPUT_DIR="/work/YOU-DARE/scrapers/data/Sweden/riks_tv_YT/"
COOKIES="/work/YOU-DARE/scrapers/scrapers/functions/cookies.txt"
FFMPEG="/work/YOU-DARE/scrapers/ffmpeg-7.0.2-amd64-static/ffmpeg"
SOURCE_NAME="riks_tv"
JL="$ROOT/metadata.jl"
DOWNLOAD_DATE=$(date +%Y-%m-%d)

# === TOKEN SETUP & SANITIZATION ===
TOKEN_URL='Ml-6y62LDIt6Nrr3MXfP49HToVOg03-kanlfhjObbKGdOYvras-Sxo9mtLZWMbIlRNzx6bMl_jJS8biYgjU6m8KFNBqXCPVMt3CE-Xd7TzzlQz_Us5LRc7bH_1lqwGQTIQ=='
TOKEN_URL="$(printf '%s' "$TOKEN_URL" | tr -d '\r\n ' | LC_ALL=C tr -cd 'A-Za-z0-9_-')"
printf '%s' "$TOKEN_URL" | od -An -t x1 | tr -d ' \n' ; echo
LC_ALL=C grep -q '^[A-Za-z0-9_-]\+$' <<<"$TOKEN_URL" && echo OK || echo BAD

# === SETUP ===
mkdir -p "$OUTPUT_DIR"
DOWNLOAD_DATE=$(date +%Y-%m-%d)
> "$JL"

# === PROCESS ===
yt-dlp "$URL" \
  --skip-download \
  --print-json \
  --ignore-errors \
  --ffmpeg-location "$FFMPEG" \
  --cookies "$COOKIES" \
  --extractor-args "youtube:po_token=web.gvs+$TOKEN_URL;player_client=mweb" \
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
' >> "$JL"

echo "✅ Metadata exported to $JL"