import csv
import json
import os

class Manual_Functions:
    @staticmethod
    def csv_to_jl(csv_path):
        """
        Converts a semicolon-delimited CSV to JSON Lines format (.jl),
        converting image_links from string to list.
        """
        if not os.path.isfile(csv_path):
            raise FileNotFoundError(f"File not found: {csv_path}")

        if not csv_path.endswith('.csv'):
            raise ValueError("Input file must be a .csv")

        jl_path = csv_path.rsplit('.', 1)[0] + '.jl'

        with open(csv_path, newline="", encoding="utf-8-sig") as infile, open(jl_path, "w", encoding="utf-8") as outfile:
            reader = csv.DictReader(infile, delimiter=';')

            for row in reader:
                # Convert image_links string → list
                if "image_links" in row and row["image_links"]:
                    links = [link.strip() for link in row["image_links"].split("|") if link.strip()]
                    row["image_links"] = links
                else:
                    row["image_links"] = []

                json.dump(row, outfile, ensure_ascii=False)
                outfile.write("\n")

        print(f"CSV converted: {csv_path}\n Saved as: {jl_path}")
        return jl_path

    @staticmethod
    def telegram_to_jl(csv_path):
        if not os.path.isfile(csv_path):
            raise FileNotFoundError(f"File not found: {csv_path}")

        if not csv_path.endswith('.csv'):
            raise ValueError("Input file must be a .csv")

        jl_path = csv_path.rsplit('_',5)[0] + '_TELEGRAM.jl'
        print(jl_path)

        try:
            with open(csv_path, newline="", encoding="utf-8-sig") as infile, open(jl_path, "w", encoding="utf-8") as outfile:
                reader = csv.DictReader(infile, delimiter=';')

                for row in reader:
                    json.dump(row, outfile, ensure_ascii=False)
                    outfile.write("\n")

            print(f"CSV converted: {csv_path}\n Saved as: {jl_path}")
            return jl_path
        except Exception as e:
            print(f'Failed to save data. Error: {e}')