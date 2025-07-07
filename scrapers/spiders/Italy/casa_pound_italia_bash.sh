#!/usr/bin/env bash

# Move into the YOU-DARE project dir
cd /work/YOU-DARE/scrapers

# Create the logs directory if it doesn't exist
mkdir -p logs

# Run spider
scrapy crawl casa_pound_italia_SPIDER > logs/spider_$(date +%Y%m%d_%H%M%S).log 2>&1

# Notify on completion
echo "Spider finished running at $(date)"