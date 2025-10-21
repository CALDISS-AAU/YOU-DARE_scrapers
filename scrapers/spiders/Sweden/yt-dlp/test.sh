COOKIES="/work/YOU-DARE/scrapers/scrapers/functions/cookies_2.txt"
FFMPEG_DIR="/work/YOU-DARE/scrapers/ffmpeg-7.0.2-amd64-static"
TOKEN_URL='Ml8BWOADPu10QwFkPKk82NV4u7ZXS4uHp-1d1kHSJ9aHQcPK3jv134ODP_A9YKIHJR8BwGPz8sujoskTublr7Nz-CfKq6bCxBpIWKOsNs8EXqYEDY0E-ZqmDvpdb8rcCVg'
TOKEN_URL="$(printf '%s' "$TOKEN_URL" | tr -d '\r\n ' | LC_ALL=C tr -cd 'A-Za-z0-9_-')"
printf '%s' "$TOKEN_URL" | od -An -t x1 | tr -d ' \n' ; echo
LC_ALL=C grep -q '^[A-Za-z0-9_-]\+$' <<<"$TOKEN_URL" && echo OK || echo BAD

yt-dlp -F "https://www.youtube.com/watch?v=Lwd7WQ8L5dQ" \
  --cookies "$COOKIES" \
  --ffmpeg-location "$FFMPEG_DIR" \
  --extractor-args "youtube:po_token=web.gvs+$TOKEN_URL;player_client=mweb" \
  -v