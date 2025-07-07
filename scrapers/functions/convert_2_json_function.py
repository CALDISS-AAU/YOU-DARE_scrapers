import csv
import json
import os
from os.path import join

class JSONFileFunctions:
    @staticmethod
    def convert_to_json(folder_path):
        for filename in os.listdir(folder_path):
            if filename.endswith(".csv"):
                csv_path = os.path.join(folder_path, filename)
                json_path = os.path.join(folder_path, filename.replace(".csv", ".json"))
                with open(csv_path, newline='', encoding='utf-8') as csvfile, \
                     open(json_path, 'w', encoding='utf-8') as jsonfile:
                    reader = csv.DictReader(csvfile)
                    rows = list(reader)
                    json.dump(rows, jsonfile, indent=2)

JSONFileFunctions.convert_to_json("/work/YOU-DARE/scrapers/data/France/le_syndicat_de_la_famille_YT/transcribed_files")