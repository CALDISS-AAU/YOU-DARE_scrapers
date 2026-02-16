import argparse
import os
import json
import random
from datetime import datetime
from pathlib import Path
from tqdm import tqdm

def load_jsonlines(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines_read = []
        for c, line in tqdm(enumerate(f)):
            line_read = json.loads(line)
            line_read.pop("article_HTML", None) # omit article source code
            lines_read.append(line_read)

        return lines_read

def save_jsonlines(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        for entry in data:
            f.write(json.dumps(entry) + '\n')

def estimate_video_length(word_count):
    lower = (word_count / 150) / 2
    upper = (word_count / 150) * 2
    return f"{lower:.1f}-{upper:.1f}"

def create_subset(data):
    if len(data) < 5:
        return data
    quintile_size = len(data) // 5
    indices = [(i * quintile_size + random.randint(0, quintile_size - 1)) for i in range(5)]
    return [data[i] for i in indices]

def process_data(data, original_filename):
    subset = create_subset(data)
    scrape_date = data[0].get('scrape_date') if data else 'N/A'
    source = data[0].get('source') if data else 'N/A'
    source_type = "Website"

    if 'YT.jl' in original_filename:
        source_type = "YouTube"
        for entry in subset:
            if 'video_text' in entry:
                word_count = len(entry['video_text'].split())
                entry['est_vid_length'] = estimate_video_length(word_count)

        pub_dates = [entry.get('publication_date') for entry in data if 'publication_date' in entry]
        pub_dates = sorted([datetime.fromisoformat(d) for d in pub_dates if d])

    print(f"Actor: {source}")
    print(f"Source type: {source_type}")
    print(f"Date of scraping: {scrape_date}")
    print(f"Total entries: {len(data)}")

    if 'YT.jl' in original_filename:
        if pub_dates:
            print(f"Oldest publication date: {pub_dates[0].isoformat()}")
            print(f"Newest publication date: {pub_dates[-1].isoformat()}")

    out_filename = original_filename.replace('.jl', '_FOR-REVIEW.jl')
    out_path = os.path.join('for-review', out_filename)
    os.makedirs('for-review', exist_ok=True)
    save_jsonlines(out_path, subset)

def main():
    parser = argparse.ArgumentParser(description="Create a subset of a scraped dataset for review.")
    parser.add_argument('-p', '--filepath', required=True, help="Path to the .jl JSON Lines file")
    args = parser.parse_args()

    filepath = args.filepath
    filename = Path(filepath).name

    if not filename.endswith('.jl'):
        print("Error: File must be a .jl JSON Lines file")
        return

    if 'SPIDER.jl' not in filename and 'YT.jl' not in filename:
        print("Error: Filename must end with SPIDER.jl or YT.jl")
    else:
        data = load_jsonlines(filepath)
        process_data(data, filename)

if __name__ == '__main__':
    main()
