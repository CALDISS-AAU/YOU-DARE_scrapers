#!/usr/bin/env bash

# Denne fil skal køres, når man starter job på UCloud. Den installerer miljøet/pakkerne, som bruges i projektet

## installerer python pakker
pip install --upgrade pip # opgraderer pip

# OBS! Nedenstående linje skal rettes så stien passer med projektet
pip install -r /work/JosefineMarianneChristensen#0406/YOU-DARE/YOU-DARE_scrapers/requirements_scrapers.txt

# playwright stuff
playwright install
playwright install-deps # webdriver drivers for driving

# yt-dlp stuff
npm install
npx tsc