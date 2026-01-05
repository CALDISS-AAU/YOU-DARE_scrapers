FFMPEG_DIR="/work/YOU-DARE/scrapers/ffmpeg-7.0.2-amd64-static"
YT_DLP_PLUGIN_DEBUG=1 yt-dlp "https://www.youtube.com/@ThaisdEscufonYT/videos" \
  --ffmpeg-location "$FFMPEG_DIR" \
  --extractor-args "youtubepot-bgutil_http:base_url=http://[::1]:4416;disable_innertube=1"
