#!/bin/bash
    echo "Processing batch..."

    /work/YOU-DARE/scrapers/yt-dlp \
      --download-archive /work/YOU-DARE/scrapers/data/Spain/vox_espana_YT/yt-dlp_files/m4a_files/archive.txt \
      --cookies /work/YOU-DARE/scrapers/scrapers/functions/cookies.txt \
      --ffmpeg-location /work/YOU-DARE/scrapers/ffmpeg-7.0.2-amd64-static \
      --format "bestaudio[ext=m4a]/bestaudio" \
      --extract-audio \
      --audio-format m4a \
      --audio-quality 0 \
      --write-info-json \
      --add-metadata \
      --compat-options no-attach-info-json \
      --output "/work/YOU-DARE/scrapers/data/Spain/vox_espana_YT/yt-dlp_files/m4a_files/%(id)s.%(ext)s" \
      --sleep-interval 4 \ 
      --max-sleep-interval 9 \
      --retries 10 \
      --ignore-errors \
      -a "/work/YOU-DARE/scrapers/data/Spain/vox_espana_YT/yt-dlp_files/m4a_files/missing_urls.txt"

    echo "Done with the shizzle"
    sleep 300