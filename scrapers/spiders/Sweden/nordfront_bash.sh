#!/usr/bin/env bash

# Move into the YOU-DARE project dir
cd /work/YOU-DARE/scrapers

# Create the logs directory if it doesn't exist
mkdir -p /work/YOU-DARE/scrapers/scrapers/spiders/Sweden/logs

# Run spider
scrapy crawl nordfront_SWE_SPIDER -a max_pages=270 > logs/spider_$(date +%Y%m%d_%H%M%S).log 2>&1

# Notify on completion
echo "Spider finished running at $(date)"