#!/bin/bash
set -euo pipefail
pip3 install -U yt-dlp jq

# === CONFIGURATION ===
URL='https://www.youtube.com/@ThaisdEscufonYT/videos'
POT_PLUGIN_DIR="/work/YOU-DARE/po-token/bgutil-ytdlp-pot-provider/plugin"
OUTPUT_DIR="/work/YOU-DARE/scrapers/data/France/ThaisdEscufon_YT"
ARCHIVE_FILE="/work/YOU-DARE/scrapers/data/France/ThaisdEscufon_YT/archive.txt"
AUDIO_OUTPUT_DIR="/work/YOU-DARE/scrapers/data/France/ThaisdEscufon_YT/m4a_files"
COOKIES="/work/YOU-DARE/scrapers/scrapers/functions/cookies.txt"
FFMPEG_DIR="/work/YOU-DARE/scrapers/ffmpeg-7.0.2-amd64-static"
SOURCE_NAME="Thaïs d'Escufon"
JL_FILE="$OUTPUT_DIR/metadata.jl"

# === SETUP ===
mkdir -p "$OUTPUT_DIR" "$AUDIO_OUTPUT_DIR"
DOWNLOAD_DATE=$(date +%Y-%m-%d)
> "$JL_FILE"
# --format "ba[ext=m4a]/ba[acodec^=opus]/ba/best"
# === PROCESS === 
yt-dlp "$URL" \
  --plugin-dirs "$POT_PLUGIN_DIR" \
  --download-archive "$ARCHIVE_FILE" \
  --cookies "$COOKIES" \
  --ffmpeg-location "$FFMPEG_DIR" \
  --extractor-args "youtubepot-bgutil_http:base_url=http://[::1]:4416;player_client=mweb;disable_innertube=1" \
  --format "ba[ext=m4a]/ba[acodec^=opus]/ba/bestaudio/18" \
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
' >> "$JL_FILE" || true
echo "☑️ Videos exported to $OUTPUT_DIR"
echo "✅ Metadata exported to $JL_FILE"