#!/usr/bin/env bash

# Denne fil skal køres, når man starter job på UCloud. Den installerer miljøet/pakkerne, som bruges i projektet

## installerer python pakker
pip install --upgrade pip # opgraderer pip

# OBS! Nedenstående linje skal rettes så stien passer med projektet
pip install -r /work/YOU-DARE/scrapers/requirements_scrapers.txt

# playwright stuff
playwright install-deps # webdriver drivers for driving
playwright install --with-deps chromium