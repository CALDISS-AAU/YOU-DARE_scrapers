import os
import shutil

txt_path = '/work/YOU-DARE/scrapers/data/Hungary/fidesz_YT/archive_missing.txt'
messy_m4a_folder_path = '/work/YOU-DARE/scrapers/data/Hungary/fidesz_YT/m4a_files'
clean_m4a_folder_path = '/work/YOU-DARE/scrapers/data/Hungary/fidesz_videos_YT/m4a_files_ytdlp'
pytube_m4a_folder_path = '/work/YOU-DARE/scrapers/data/Hungary/fidesz_videos_YT/m4a_files_pytube'

if not os.path.exists(clean_m4a_folder_path):
    os.mkdir(clean_m4a_folder_path)

video_ids = []

with open(txt_path, 'r') as txt:
    for line in txt:
        parts = line.strip().split()
        video_ids.append(parts[1])

print(len(video_ids))

for video in video_ids:
    src = os.path.join(messy_m4a_folder_path, f'{video}.m4a')
    dest = os.path.join(clean_m4a_folder_path, f'{video}.m4a')

    if os.path.exists(src):
        if not os.path.exists(dest):
            shutil.copy2(src, dest)
            print(f'Copied {video} sucessfully!')
        else: 
            print(f'Skipped {video}')
    else:
        print(f"Couldn't copy {video}")

ytdlp_m4a_files = {f for f in os.listdir(clean_m4a_folder_path) if f.endswith(".m4a")}
pytube_m4a_files = {f for f in os.listdir(pytube_m4a_folder_path) if f.endswith(".m4a")}

duplicates = ytdlp_m4a_files.intersection(pytube_m4a_files)

if duplicates:
    print(f'Found {len(duplicates)} duplicates:\n{duplicates}')
else:
    print(f'No duplicates found')