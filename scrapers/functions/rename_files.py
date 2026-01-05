import re
import glob
import os

video_dir = '/work/YOU-DARE/scrapers/data/France/ThaisdEscufon_YT/m4a_files/*.m4a'
pattern = r'\[([^\]]+)\]'   # Captures the text inside [ ]

# Finding all files
files = glob.glob(video_dir)

# Looping over files, renaming and save the files
for file_path in files:
    filename = os.path.basename(file_path)
    folder = os.path.dirname(file_path)

    match = re.search(pattern, filename)
    if not match:
        print(f"Skipping: no bracket code in {filename}")
        continue
    # Extracting the matches
    code = match.group(1)

    new_filename = code + '.m4a'
    new_path = os.path.join(folder, new_filename)

    print(f"Renaming:\n  {filename}\n→ {new_filename}")
    os.rename(file_path, new_path)