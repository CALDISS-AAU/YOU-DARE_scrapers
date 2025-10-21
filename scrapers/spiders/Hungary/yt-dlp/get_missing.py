import json
import re

file_path = '/work/YOU-DARE/scrapers/data/Hungary/fidesz_videos_YT/not_downloaded_maybe.jl'
not_downloaded_maybe = [] # Initialize as a list to store all the JSON objects

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        # Iterate over each line in the file
        for line in f:
            # 1. Strip any leading/trailing whitespace (crucial for removing the newline character)
            stripped_line = line.strip()
            
            # 2. Check if the line is not empty before attempting to parse
            if stripped_line:
                try:
                    # 3. Use json.loads() to parse the JSON string (the line) into a Python object
                    json_object = json.loads(stripped_line)
                    not_downloaded_maybe.append(json_object)
                except json.JSONDecodeError as e:
                    # Handle cases where a line might be malformed JSON
                    print(f"Error decoding JSON on line: {stripped_line[:50]}... Error: {e}")

    print(f"Successfully loaded {len(not_downloaded_maybe)} objects from the file.")

except FileNotFoundError:
    print(f"Error: File not found at {file_path}")


# The regex pattern to match the dynamic video ID
regex_pattern = re.compile(r"DOWNLOAD:[A-Za-z0-9_-]+ is unavailable")

# Create a new list to store the filtered rows
unavailable_rows_only_regex = []

for row in not_downloaded_maybe:
    # Check for the 'error' key and ensure it's a list
    if 'error' in row and isinstance(row['error'], list):
        error_list = row['error']
        
        # Check if ANY string in error_list matches the regex pattern
        for error_string in error_list:
            if regex_pattern.search(error_string):
                unavailable_rows_only_regex.append(row)
                break # Move to the next row once a match is found

     
print(f"Rows matching ONLY the video unavailability pattern: {len(unavailable_rows_only_regex)}")

urls = [
    row['url'] 
    for row in unavailable_rows_only_regex
    if 'url' in row # Safety check: ensure the 'url' key exists
    ]


with open('/work/YOU-DARE/scrapers/data/Hungary/fidesz_videos_YT/unavailable_urls.txt', 'w') as file:
    for item in urls:
        file.write(item + '\n')