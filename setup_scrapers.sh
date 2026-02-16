#!/usr/bin/env bash

## install python stuff
pip install --upgrade pip # opgraderer pip

# packages
pip install -r requirements.txt

# playwright stuff
playwright install
playwright install-deps # webdriver drivers for driving

# telegram stuff
pip3 install telepathy
pip3 install cryptg
