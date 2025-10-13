import json
import pandas as pd
import dateparser
import re
import os
import numpy as np
import traceback
import shutil


class Transcriber_data_Functions:
    def add_transcribed_text_to_video_data(self, dataset_path, transcriptions_dir):
        """
        Convenience function to:
        1. Extract text from transcription files.
        2. Merge with the videos dataset.
        
        Output is saved in the same folder as the videos dataset with a name
        matching the folder name.

        Args:
            dataset_path (str): Full path to 'videos.jl'.
            transcriptions_dir (str): Directory containing raw transcription .json files.
        """
        # Step 1: Create intermediate file path for extracted text
        temp_transcript_path = os.path.join(transcriptions_dir, 'combined_text_dataset.jl')

        # Step 2: Generate text dataset
        self.make_text_dataset_from_transcriptions(transcriptions_dir, temp_transcript_path)

        # Step 3: Merge with original dataset
        self.merge_datasets_on_audio_name(dataset_path, temp_transcript_path)

    def extract_text_from_jsonl(self, file_path):
        all_texts = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f) # json either as list [ or dict {

                if isinstance(data, list): # assumes that segments are in list or one-level dictionary with top key 'segments'
                    segments = data
                else:
                    segments = data.get('segments', [])
                    
                for segment in segments:
                    text = segment.get('text')
                    if text:
                        all_texts.append(text)
        except Exception as e:
            print(f'Failed to load data from {file_path}. Error: {e}')
            return []

        full_text = ' '.join(all_texts)
        return full_text

    def make_text_dataset_from_transcriptions(self, transcriptions_dir, output_path):
        """
        Processes transcription JSON files in a directory and writes a JSONL file with
        'file_name' (cleaned to match original metadata) and 'text' fields.
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as out_file:
                for file_name in os.listdir(transcriptions_dir):
                    if file_name.endswith('.json'):
                        file_path = os.path.join(transcriptions_dir, file_name)
                        full_text = self.extract_text_from_jsonl(file_path)

                        # Clean the filename to strip model/language suffix
                        # Extract the video_id from filenames like INIyA3MVQ6Q_large-v3_it.json
                        cleaned_name = os.path.splitext(file_name)[0]
                        match = re.match(r"^([a-zA-Z0-9_-]{11})", cleaned_name)
                        if not match:
                            print(f"Could not extract video_id from {file_name}")
                            continue
                        video_id = match.group(1)

                        out_file.write(json.dumps({
                            'file_name': video_id,
                            'video_text': full_text
                        }) + '\n')
        except Exception as e:
            print(f'Failed to process transcriptions from {transcriptions_dir}. Error: {e}')
            return []
    
    def merge_datasets_on_audio_name(self, dataset_path, transcript_path):
        """
        Merges metadata and transcription datasets based on normalized audio file names,
        and saves the result to a .jl file named after the dataset's parent folder.
        """
        try:
            # Step 1: Load transcriptions into a normalized lookup dictionary
            transcription_lookup = {}
            with open(transcript_path, 'r', encoding='utf-8') as tf:
                for line in tf:
                    data = json.loads(line)
                    key = data['file_name'].strip().lower()
                    transcription_lookup[key] = data['video_text']

            # Step 2: Merge with dataset entries
            merged_data = []
            unmatched_files = []
            with open(dataset_path, 'r', encoding='utf-8') as df:
                for line in df:
                    entry = json.loads(line)
                    raw_name = entry.get('video_id')
                    normalized_name = raw_name.strip().lower() if raw_name else None

                    if normalized_name and normalized_name in transcription_lookup:
                        entry['video_text'] = transcription_lookup[normalized_name]
                        # print(f"Matched: {raw_name}")
                    else:
                        unmatched_files.append(raw_name)
                        # print(f"No match for: {raw_name}")

                    merged_data.append(entry)

            # Step 3: Determine output path
            folder_path = os.path.dirname(dataset_path)
            parent_folder_name = os.path.basename(folder_path)
            output_path = os.path.join(folder_path, f'{parent_folder_name}.jl')

            # Step 4: Write merged output
            with open(output_path, 'w', encoding='utf-8') as out_file:
                for item in merged_data:
                    out_file.write(json.dumps(item) + '\n')

            print(f'Merged file saved to: {output_path}')
            if unmatched_files:
                print(f"\nUnmatched entries: {len(unmatched_files)}")
                for f in unmatched_files: # print's the name of all unmatched files
                    print(f" - {f}")

        except Exception as e:
            print(f'Failed to merge datasets. Error: {e}\n\n\n')

    @staticmethod
    def clean_transcribed_audio_files_setup(base_path):
        """
        Enhanced setup that:
        - Creates m4a_files_TEMP and transcribed folders if missing.
        - Copies .m4a files to TEMP only if TEMP does not exist.
        - Deletes already transcribed files from TEMP.
        - Deletes empty files in TEMP during initial run.
        - Deletes TEMP folder if it's empty.
        - Prints useful folder stats.
        """
        m4a_dir = os.path.join(base_path, 'm4a_files_TEMP')
        original_m4a_dir = os.path.join(base_path, 'm4a_files')
        transcribed_dir = os.path.join(base_path, 'transcribed')

        # Create TEMP and copy files if it doesn't exist
        first_run = False
        if not os.path.exists(m4a_dir):
            print(f"Creating temp audio folder: {m4a_dir}")
            os.makedirs(m4a_dir, exist_ok=True)
            first_run = True
            if os.path.exists(original_m4a_dir):
                for file in os.listdir(original_m4a_dir):
                    if file.endswith('.m4a'):
                        src = os.path.join(original_m4a_dir, file)
                        dst = os.path.join(m4a_dir, file)
                        shutil.copy2(src, dst)
                print(f"✅ Copied audio files from {original_m4a_dir} to {m4a_dir}")
            else:
                print(f"Original m4a_files folder not found: {original_m4a_dir}")
                return
        else:
            print(f"Temp audio folder already exists: {m4a_dir}")

        # Create transcribed folder if missing
        if not os.path.exists(transcribed_dir):
            print(f"Creating transcription folder: {transcribed_dir}")
            os.makedirs(transcribed_dir, exist_ok=True)
        else:
            print(f"Transcribed folder already exists: {transcribed_dir}")

        # Delete empty files (0-byte) in TEMP — only on first run
        if first_run:
            removed_empty = 0
            for file in os.listdir(m4a_dir):
                file_path = os.path.join(m4a_dir, file)
                if os.path.isfile(file_path) and os.path.getsize(file_path) == 0:
                    os.remove(file_path)
                    removed_empty += 1
            if removed_empty > 0:
                print(f"Removed {removed_empty} empty files from TEMP folder")

        # Remove already transcribed audio files
        Transcriber_data_Functions.clean_transcribed_audio_files(m4a_dir, transcribed_dir)

        # Auto-remove TEMP folder if empty
        if os.path.exists(m4a_dir) and not any(os.scandir(m4a_dir)):
            shutil.rmtree(m4a_dir)
            print(f"TEMP folder was empty and has been deleted: {m4a_dir}")

        # Final stats
        def count_files(path, endswith=None):
            return len([
                f for f in os.listdir(path)
                if os.path.isfile(os.path.join(path, f)) and (endswith is None or f.endswith(endswith))
            ]) if os.path.exists(path) else 0

        original_m4a_count = count_files(original_m4a_dir, '.m4a')
        empty_original = len([
            f for f in os.listdir(original_m4a_dir)
            if f.endswith('.m4a') and os.path.getsize(os.path.join(original_m4a_dir, f)) == 0
        ]) if os.path.exists(original_m4a_dir) else 0
        temp_count = count_files(m4a_dir, '.m4a')
        transcribed_count = count_files(transcribed_dir, '.json')

        print("\nFolder Stats:")
        print(f" - Original m4a_files: {original_m4a_count}")
        print(f" - Empty files in original m4a_files: {empty_original}")
        print(f" - Files in TEMP folder: {temp_count}")
        print(f" - Transcribed JSON files: {transcribed_count}")

    @staticmethod
    def clean_transcribed_audio_files(m4a_dir, transcribed_dir):
        """
        Deletes .m4a audio files in m4a_dir if a transcription file exists in transcribed_dir
        that starts with the same video ID (first 11 chars of the filename).
        """
        m4a_files = [f for f in os.listdir(m4a_dir) if f.endswith('.m4a')]
        transcribed_files = os.listdir(transcribed_dir)

        transcribed_ids = set()
        for fname in transcribed_files:
            if fname.endswith('.json'):
                base = os.path.splitext(fname)[0]
                match = re.match(r"^([a-zA-Z0-9_-]{11})", base)
                if match:
                    video_id = match.group(1)
                    transcribed_ids.add(video_id)
                else:
                    print(f"Could not extract video ID from: {fname}")

        deleted = 0
        for audio_file in m4a_files:
            video_id = os.path.splitext(audio_file)[0]

            if video_id in transcribed_ids:
                full_path = os.path.join(m4a_dir, audio_file)
                os.remove(full_path)
                deleted += 1
                print(f"🗑️ Removed already transcribed file: {audio_file}")

        print(f"\nDone. Removed {deleted} files from '{m4a_dir}'.")