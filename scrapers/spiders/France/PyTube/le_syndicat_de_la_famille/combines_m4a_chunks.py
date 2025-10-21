import os
import shutil

input_folder = "/work/YOU-DARE/scrapers/data/France/le_syndicat_de_la_famille_YT/m4a_files_chunks"
output_folder = "/work/YOU-DARE/scrapers/data/France/le_syndicat_de_la_famille_YT/m4a_files"

os.makedirs(output_folder, exist_ok=True)

for root, _, files in os.walk(input_folder):
    for file in files:
        if file.endswith(".m4a"):
            src_path = os.path.join(root, file)
            dst_path = os.path.join(output_folder, file)
            shutil.copy2(src_path, dst_path)

print("All .m4a files have been copied to:", output_folder)
