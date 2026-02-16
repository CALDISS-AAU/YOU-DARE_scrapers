#!/usr/bin/env bash

# Denne fil skal køres, når man starter job på UCloud. Den installerer miljøet/pakkerne, som bruges i projektet

## installerer python pakker
pip install --upgrade pip # opgraderer pip

# OBS! Nedenstående linje skal rettes så stien passer med projektet
pip install -r /work/YOU-DARE/scrapers/requirements_snapshot.txt
#/work/YOU-DARE/scrapers/requirements_scrapers.txt
#/work/YOU-DARE/environment/requirements.txt
#/work/YOU-DARE/scrapers/requirements_snapshot.txt

# playwright stuff
playwright install
playwright install-deps # webdriver drivers for driving

# telegram stuff
pip3 install telepathy
pip3 install cryptg