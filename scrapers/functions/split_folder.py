import os
import shutil

src_dir = '/work/YOU-DARE/scrapers/data/France/le_syndicat_de_la_famille_YT/m4a_files'

files = [f for f in os.listdir(src_dir) if os.path.isfile(os.path.join(src_dir, f))]

chunk_size = 75
for i in range(0, len(files), chunk_size):
    chunk_folder = os.path.join(src_dir, f"m4a_chunk_{i // chunk_size + 1:02}")
    os.makedirs(chunk_folder, exist_ok=True)
    for f in files[i:i+chunk_size]:
        shutil.move(os.path.join(src_dir, f), os.path.join(chunk_folder, f))

