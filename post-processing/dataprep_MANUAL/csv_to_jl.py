''' To run this scraper from bash do the following:
        cd ./path/to/YOU-DARE_scrapers-folder
        python -m post-processing.dataprep_MAUAL.csv_to_jl
    Replace all paths with actual paths!
''' 

import pandas as pd
from pathlib import Path

file_path = Path("./data/Country/source_MANUAL/source_MANUAL.csv")

df = pd.read_csv(file_path, sep=";")

output_path = file_path.with_suffix(".jl")

df.to_json(output_path, orient="records", lines=True)