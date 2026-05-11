#!/bin/bash
set -euo pipefail
pip3 install -U yt-dlp jq

URL="https://www.youtube.com/c/Riksstudios/videos"
ROOT="/work/YOU-DARE/scrapers/data/Sweden/riks_tv_YT"
ARCHIVE="$ROOT/archive.txt"
AUDIO_DIR="$ROOT/m4a_files"
COOKIES="/work/YOU-DARE/scrapers/scrapers/functions/cookies.txt"
FFMPEG="/work/YOU-DARE/scrapers/ffmpeg-7.0.2-amd64-static/ffmpeg"
SOURCE_NAME="riks_tv"
JL="$ROOT/metadata.jl"
DOWNLOAD_DATE=$(date +%Y-%m-%d)

mkdir -p "$AUDIO_DIR"
: > "$JL"

# ---------- PASS 1: no cookies (Android/TV-simply to dodge SABR) ----------
yt-dlp "$URL" \
  --download-archive "$ARCHIVE" \
  --ffmpeg-location "$FFMPEG" \
  --extractor-args "youtube:player_client=android,tv_simply,web" \
  --format "ba[ext=m4a]/ba[acodec^=opus]/ba/best" \
  --extract-audio --audio-format m4a --audio-quality 0 \
  --add-metadata \
  --output "$AUDIO_DIR/%(id)s.%(ext)s" \
  --sleep-interval 4.5 --max-sleep-interval 10 \
  --retries 10 --ignore-errors --ignore-no-formats-error \
  --print-json --verbose \
| jq -c --arg dl "$DOWNLOAD_DATE" --arg src "$SOURCE_NAME" \
    '{video_id: .id, video_title: .title, video_link: .webpage_url, publication_date: .upload_date, scrape_date: $dl, source: $src}' \
>> "$JL"

# ---------- PASS 2: with cookies (for gated videos), accept web/SABR fallback ----------
yt-dlp "$URL" \
  --download-archive "$ARCHIVE" \
  --cookies "$COOKIES" \
  --ffmpeg-location "$FFMPEG" \
  --extractor-args "youtube:player_client=web" \
  --format "ba/bestaudio/18" \
  --extract-audio --audio-format m4a --audio-quality 0 \
  --add-metadata \
  --output "$AUDIO_DIR/%(id)s.%(ext)s" \
  --sleep-interval 4.5 --max-sleep-interval 10 \
  --retries 10 --ignore-errors --ignore-no-formats-error \
  --print-json --verbose \
| jq -c --arg dl "$DOWNLOAD_DATE" --arg src "$SOURCE_NAME" \
    '{video_id: .id, video_title: .title, video_link: .webpage_url, publication_date: .upload_date, scrape_date: $dl, source: $src}' \
>> "$JL"

echo "☑️ Audio files in $AUDIO_DIR"
echo "✅ Metadata exported to $JL"
