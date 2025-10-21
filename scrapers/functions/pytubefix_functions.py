from pytubefix import Channel
from pytubefix import Playlist
from pytubefix import YouTube
from pathlib import Path
from datetime import datetime, date
from collections import OrderedDict
from pytubefix import exceptions as ptfx_exc

import dateparser
import json
import jsonlines
import time
import re
import os

class Pytubefix_Functions:
    @staticmethod
    def parse_partial_date(date_str):
        parsed = dateparser.parse(
            date_str,
            settings={
                'PREFER_DAY_OF_MONTH': 'first',
                'PREFER_DATES_FROM': 'past',
            }
        )
        if not parsed:
            raise ValueError(f"Invalid date input: '{date_str}'")
        return parsed.date()

    @staticmethod
    def extract_source(url):
        '''
        Extract channel name
        '''
        pattern = r'@([^/]+)'
        match = re.search(pattern, url)
        return match.group(1) if match else 'Unknown'

    @staticmethod
    def generate_output_path(file, nesting_level = 4):
        ''' Generates an output path for Pytubefix scrapers.
            Variables:  file should ALWAYS be set to __file__ (this gives the path to the current script that calls the function)
                        nesting_level is automatically set to 4 but can be changed
                        Assumed path: /work/YOU-DARE/scrapers/scrapers/spiders/Country/PyTube -> nesting_level = 4 from the first scrapers
        '''
        script_path = Path(file).resolve() # This gets the path of the script passed as "file"
        country = script_path.parents[nesting_level-3].name # This gets the country from the script's parent folder
        script_name = script_path.stem # This gets the script name without '.py'
        output_path = script_path.parents[nesting_level] / 'data' / country / script_name # This is the output path - script_path.parents[4] = '/work/YOU-DARE/scrapers'
        print(f'This is the generated output path: {output_path}')
        return output_path

    @staticmethod
    def pytubefix_from_channel_jsonlines(url: str, output_path, source='', from_date=None, to_date=None, flush_every=100, videos = True, shorts = False, live = False):
        '''Same functionality but writes to file every `flush_every` videos.'''
        from pytubefix import Channel  # Redundant if already globally imported

        # Setup
        channel = Channel(url, use_oauth=True, allow_oauth_cache=True)
        output_path.mkdir(parents=True, exist_ok=True)
        jsonlines_path = output_path / 'videos.jl'

        if not source:
            source = Pytubefix_Functions.extract_source(url)

        timestamp = datetime.now().strftime('%Y-%m-%d')
        existing_videos = set()

        if jsonlines_path.exists():
            with jsonlines_path.open('r', encoding='utf-8') as f:
                for line in f:
                    existing_videos.add(json.loads(line)['video_link'])

        videos_to_scrape = []
        if videos:
            videos_add = [video for video in channel.videos if video.watch_url not in existing_videos]
            videos_to_scrape = videos_to_scrape + videos_add

        if shorts:
            videos_add = [short for short in channel.shorts if short.watch_url not in existing_videos]
            videos_to_scrape = videos_to_scrape + videos_add
        
        if live:
            videos_add = [live for live in channel.live if live.watch_url not in existing_videos]
            videos_to_scrape = videos_to_scrape + videos_add
        video_count = len(videos_to_scrape)
        print(f"Starting to scrape {video_count} new videos...")

        buffer = []  # Temporarily store video data

        for idx, video in enumerate(videos_to_scrape, start=1):
            try:
                if video.publish_date: # check if publish date is available (returns None otherwise)
                    pub_date = video.publish_date.date()
                    if from_date and pub_date < from_date:
                        print(f"[{idx}/{video_count}] Encountered video older than from_date, stopping further scraping.")
                        break
                    if to_date and pub_date > to_date:
                        print(f"[{idx}/{video_count}] Skipping: {video.title} — newer than to_date")
                        continue

                    pub_date_write = video.publish_date.isoformat() # date to write to data

                else: # set missing date value ("") if date not available
                    print(f"[{idx}/{video_count}] Not possible to retrieve publish date from {video.title} — set as missing/empty string")
                    pub_date_write = ""


                video_data = {
                    'scrape_date': timestamp,
                    'video_title': video.title,
                    'source': source,
                    'publication_date': pub_date_write,
                    'video_link': video.watch_url,
                    'video_id': video.video_id,
                }

                buffer.append(video_data)
                print(f"[{idx}/{video_count}] Scraped: {video.title}")

                # Write to file every `flush_every` videos
                if len(buffer) >= flush_every:
                    with jsonlines.open(jsonlines_path, mode='a') as writer:
                        writer.write_all(buffer)
                    print(f"💾 Flushed {len(buffer)} videos to disk.")
                    buffer.clear()

            except Exception as e:
                print(f"[{idx}/{video_count}] Failed to process '{video.title}'. Error: {e}")

        # Write any remaining videos
        if buffer:
            with jsonlines.open(jsonlines_path, mode='a') as writer:
                writer.write_all(buffer)
            print(f"💾 Flushed final {len(buffer)} videos to disk.")

        print(f"✅ Finished! Scraped {video_count} new videos.")


    @staticmethod
    def pytubefix_from_channel_audio(url: str, output_path, from_date=None, to_date=None, videos = True, shorts = False, live = False, check_for_downloaded = False):
        from pytubefix import Channel  # ensure imported at top if not global

        channel = Channel(url, use_oauth=True, allow_oauth_cache=True)
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        m4a_folder_path = output_path / 'm4a_files'
        m4a_folder_path.mkdir(parents=True, exist_ok=True)
        failed_path = output_path / 'not_downloaded.jl'

        downloaded_count = 0

        # Check already downloaded files
        if check_for_downloaded:
            downloaded_files_ids = [file.removesuffix('.m4a') for file in os.listdir(m4a_folder_path) if file.endswith('.m4a')]
        else:
            downloaded_files_ids = []

        # Track video_ids we've already logged as failed to avoid duplication
        logged_failures = set()

        # Load previously failed attempts into memory
        if failed_path.exists():
            with jsonlines.open(failed_path, mode='r') as reader:
                for item in reader:
                    try:
                        title, video_id, _ = item["error"]
                        logged_failures.add(video_id)
                    except Exception as e:
                        print(f"Skipping malformed failure entry: {item} — {e}")

        videos_to_scrape = []
        if videos:
            videos_add = [video for video in channel.videos if video.video_id not in downloaded_files_ids]
            videos_to_scrape = videos_to_scrape + videos_add

        if shorts:
            videos_add = [short for short in channel.shorts if short.video_id not in downloaded_files_ids]
            videos_to_scrape = videos_to_scrape + videos_add
        
        if live:
            videos_add = [live for live in channel.live if live.video_id not in downloaded_files_ids]
            videos_to_scrape = videos_to_scrape + videos_add

        video_count = len(videos_to_scrape)

        print(f"Downloading audio for {video_count} new videos...")

        for idx, video in enumerate(videos_to_scrape, start=1):

            if video.publish_date: # check if publish date is available (returns None otherwise)
                pub_date = video.publish_date.date()
                if from_date and pub_date < from_date:
                    print(f"[{idx}/{video_count}] Encountered video older than from_date, stopping further scraping.")
                    break
                if to_date and pub_date > to_date:
                    print(f"[{idx}/{video_count}] Skipping: {video.title} — newer than to_date")
                    continue

            else: 
                print(f"[{idx}/{video_count}] Not possible to retrieve publish date from {video.title} — downloading audio regardless of date filter")
                

            video_title = video.title
            video_id = video.video_id
            file_name = f"{video_id}.m4a"
            file_path = m4a_folder_path / file_name

            if file_path.exists():
                print(f"[{idx}/{video_count}] Already downloaded, skipping: {video_title}")
                continue

            try:
                audio_stream = video.streams.filter(only_audio=True).first()
                if audio_stream is None:
                    raise ValueError("No audio stream available.")

                audio_stream.download(output_path=m4a_folder_path, filename=file_name)
                downloaded_count += 1
                print(f"[{idx}/{video_count}] Downloaded audio: {video_title}")

            except Exception as e:
                print(f"[{idx}/{video_count}] Failed to download '{video_title}': {e}")

                if video_id not in logged_failures:
                    failure_record = {
                        "error": [video_title, video_id, str(e)],
                        "retries": 0
                    }
                    logged_failures.add(video_id)

                    # Immediately append to not_downloaded.jl
                    with jsonlines.open(failed_path, mode='a') as writer:
                        writer.write(failure_record)

        print(f"Finished downloading audio. {downloaded_count} succeeded. Failures logged to {failed_path}")

    @staticmethod
    def pytubefix_from_channel(url:str, file, nesting_level = 4, source = '', output_path=None, from_date=None, to_date=None, videos=True, shorts=False, live=False, check_for_downloaded=False):
        ''' Takes a URL, a file (should always be __file__). Generates an output path for the data, a jsonlines file containing scraped data and a folder with all audio files. '''
        if not output_path:
            generated_output_path = Pytubefix_Functions.generate_output_path(file, nesting_level)
        else:
            generated_output_path = Path(output_path)
        Pytubefix_Functions.pytubefix_from_channel_jsonlines(url, generated_output_path, source, from_date=from_date, to_date=to_date, videos=videos, shorts=shorts, live=live)
        Pytubefix_Functions.pytubefix_from_channel_audio(url, generated_output_path, from_date=from_date, to_date=to_date, videos=videos, shorts=shorts, live=live, check_for_downloaded=check_for_downloaded)
        print(f'The YouTube channel {url} has been fully scraped! \nThe scraped data can be found at {generated_output_path}.')
        return generated_output_path
    

    @staticmethod
    def retry_failed_downloads(output_path, max_attempts=3, sleep_seconds=1):
        '''
        Retries downloading audio files listed in not_downloaded.jl.
        Adds retry_error_i keys and a "retries" field (shown first).
        Preserves original "error" field. Does not drop any info.
        '''
        output_path = Path(output_path)
        m4a_folder_path = output_path / 'm4a_files'
        failed_path = output_path / 'not_downloaded.jl'

        if not failed_path.exists():
            print("No failed downloads to retry.")
            return

        for attempt in range(1, max_attempts + 1):
            print(f"\n--- Attempt {attempt}/{max_attempts} ---")

            failed_videos = []
            with jsonlines.open(failed_path, mode='r') as reader:
                for item in reader:
                    try:
                        title, video_id, _ = item["error"]
                        retries = item.get("retries", 0)
                        failed_videos.append((title, video_id, item, retries))
                    except Exception as parse_error:
                        print(f"Skipping malformed line: {item} — {parse_error}")

            if not failed_videos:
                print("Nothing to retry — all videos downloaded.")
                failed_path.unlink()
                break

            still_failed = []

            for idx, (title, video_id, item, retries) in enumerate(failed_videos, start=1):
                file_name = f"{video_id}.m4a"
                file_path = m4a_folder_path / file_name

                if file_path.exists():
                    print(f"[{idx}] Already downloaded: {title}")
                    continue

                try:
                    yt = YouTube(
                        f"https://www.youtube.com/watch?v={video_id}",
                        use_oauth=True,
                        allow_oauth_cache=True
                    )
                    audio_stream = yt.streams.filter(only_audio=True).first()
                    if audio_stream is None:
                        raise ValueError("No audio stream available.")

                    audio_stream.download(output_path=m4a_folder_path, filename=file_name)
                    print(f"[{idx}] Successfully downloaded: {title}")

                except Exception as e:
                    print(f"[{idx}] Still failed: {title} — {e}")

                    # Create a new OrderedDict with desired key order
                    ordered = OrderedDict()
                    ordered["error"] = item["error"]
                    ordered["retries"] = retries + 1
                    # Copy all previous retry_error_i keys
                    for key in sorted(item.keys()):
                        if key.startswith("retry_error_"):
                            ordered[key] = item[key]
                    # Add new retry error
                    ordered[f"retry_error_{retries}"] = str(e)

                    still_failed.append(ordered)

                time.sleep(sleep_seconds)

            if still_failed:
                with jsonlines.open(failed_path, mode='w') as writer:
                    writer.write_all(still_failed)
                print(f"{len(still_failed)} videos still failed. Will retry next round...")
            else:
                print("🎉 All failed downloads recovered!")
                failed_path.unlink()
                break

    @staticmethod
    def download_all_audio_until_complete(channel_url, output_path, max_rounds=10, sleep_seconds=2):
        ''' Keeps running until all videos in videos.jl have a corresponding .m4a file.
            Handles retries and resumes after crashes.
        '''
        output_path = Path(output_path)
        m4a_folder = output_path / 'm4a_files'
        video_list_path = output_path / 'videos.jl'

        if not video_list_path.exists():
            raise FileNotFoundError(f"{video_list_path} not found. Run metadata scrape first.")

        total_expected = sum(1 for _ in video_list_path.open('r', encoding='utf-8'))

        for round in range(1, max_rounds + 1):
            print(f"\n🔁 Audio Download Round {round} of {max_rounds} 🔁")

            # Try new downloads
            Pytubefix_Functions.pytubefix_from_channel_audio(
                url=channel_url,
                output_path=output_path,
                from_date=None,
                to_date=None
            )

            # Retry any that failed previously
            Pytubefix_Functions.retry_failed_downloads(output_path)

            # Count how many .m4a files exist now
            m4a_downloaded = len(list(m4a_folder.glob("*.m4a")))
            print(f"🎧 Progress: {m4a_downloaded}/{total_expected} downloaded")

            if m4a_downloaded >= total_expected:
                print("🎉 All audio files successfully downloaded!")
                break

            print(f"⏳ Sleeping {sleep_seconds} seconds before next round...")
            time.sleep(sleep_seconds)

        else:
            print("⚠️ Reached max retries, some audio files may still be missing.")
    
    @staticmethod
    def pytubefix_from_playlist_jsonlines(url: str, output_path, source='', from_date=None, to_date=None, flush_every=100):
        '''Same functionality but writes to file every `flush_every` videos.'''

        # Setup
        playlist = Playlist(url, use_oauth=True, allow_oauth_cache=True)
        output_path.mkdir(parents=True, exist_ok=True)
        jsonlines_path = output_path / 'videos.jl'

        if not source:
            source = Pytubefix_Functions.extract_source(url)

        timestamp = datetime.now().strftime('%Y-%m-%d')
        existing_videos = set()

        if jsonlines_path.exists():
            with jsonlines_path.open('r', encoding='utf-8') as f:
                for line in f:
                    existing_videos.add(json.loads(line)['video_link'])

        videos_to_scrape = [video for video in playlist.videos if video.watch_url not in existing_videos]
        video_count = len(videos_to_scrape)
        print(f"Starting to scrape {video_count} new videos...")

        buffer = []  # Temporarily store video data

        for idx, video in enumerate(videos_to_scrape, start=1):
            try:
                if video.publish_date: # check if publish date is available (returns None otherwise)
                    pub_date = video.publish_date.date()
                    if from_date and pub_date < from_date:
                        print(f"[{idx}/{video_count}] Encountered video older than from_date, stopping further scraping.")
                        break
                    if to_date and pub_date > to_date:
                        print(f"[{idx}/{video_count}] Skipping: {video.title} — newer than to_date")
                        continue

                    pub_date_write = video.publish_date.isoformat() # date to write to data

                else: # set missing date value ("") if date not available
                    print(f"[{idx}/{video_count}] Not possible to retrieve publish date from {video.title} — set as missing/empty string")
                    pub_date_write = ""

                video_data = {
                    'scrape_date': timestamp,
                    'video_title': video.title,
                    'source': source,
                    'publication_date': pub_date_write,
                    'video_link': video.watch_url,
                    'video_id': video.video_id,
                }

                buffer.append(video_data)
                print(f"[{idx}/{video_count}] Scraped: {video.title}")

                # Write to file every `flush_every` videos
                if len(buffer) >= flush_every:
                    with jsonlines.open(jsonlines_path, mode='a') as writer:
                        writer.write_all(buffer)
                    print(f"💾 Flushed {len(buffer)} videos to disk.")
                    buffer.clear()

            except Exception as e:
                print(f"[{idx}/{video_count}] Failed to process '{video.title}'. Error: {e}")

        # Write any remaining videos
        if buffer:
            with jsonlines.open(jsonlines_path, mode='a') as writer:
                writer.write_all(buffer)
            print(f"💾 Flushed final {len(buffer)} videos to disk.")

        print(f"✅ Finished! Scraped {video_count} new videos.")


    @staticmethod
    def pytubefix_from_playlist_audio(url: str, output_path, from_date=None, to_date=None, check_for_downloaded=False):

        playlist = Playlist(url, use_oauth=True, allow_oauth_cache=True)
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        m4a_folder_path = output_path / 'm4a_files'
        m4a_folder_path.mkdir(parents=True, exist_ok=True)
        failed_path = output_path / 'not_downloaded.jl'

        video_count = len(playlist.videos)
        downloaded_count = 0

        # Check already downloaded files
        if check_for_downloaded:
            downloaded_files_ids = [file.removesuffix('.m4a') for file in os.listdir(m4a_folder_path) if file.endswith('.m4a')]
        else:
            downloaded_files_ids = []

        # Track video_ids we've already logged as failed to avoid duplication
        logged_failures = set()

        # Load previously failed attempts into memory
        if failed_path.exists():
            with jsonlines.open(failed_path, mode='r') as reader:
                for item in reader:
                    try:
                        title, video_id, _ = item["error"]
                        logged_failures.add(video_id)
                    except Exception as e:
                        print(f"Skipping malformed failure entry: {item} — {e}")

        # Video list
        videos_to_scrape = [video for video in playlist.videos if video.video_id not in downloaded_files_ids]

        video_count = len(videos_to_scrape)

        print(f"Downloading audio for {video_count} new videos...")

        for idx, video in enumerate(videos_to_scrape, start=1):
            if video.publish_date: # check if publish date is available (returns None otherwise)
                pub_date = video.publish_date.date()
                if from_date and pub_date < from_date:
                    print(f"[{idx}/{video_count}] Encountered video older than from_date, stopping further scraping.")
                    break
                if to_date and pub_date > to_date:
                    print(f"[{idx}/{video_count}] Skipping: {video.title} — newer than to_date")
                    continue
            
            else: 
                print(f"[{idx}/{video_count}] Not possible to retrieve publish date from {video.title} — downloading audio regardless of date filter")
           
            video_title = video.title
            video_id = video.video_id
            file_name = f"{video_id}.m4a"
            file_path = m4a_folder_path / file_name

            if file_path.exists():
                print(f"[{idx}/{video_count}] Already downloaded, skipping: {video_title}")
                continue

            try:
                audio_stream = video.streams.filter(only_audio=True).first()
                if audio_stream is None:
                    raise ValueError("No audio stream available.")

                audio_stream.download(output_path=m4a_folder_path, filename=file_name)
                downloaded_count += 1
                print(f"[{idx}/{video_count}] Downloaded audio: {video_title}")

            except Exception as e:
                print(f"[{idx}/{video_count}] Failed to download '{video_title}': {e}")

                if video_id not in logged_failures:
                    failure_record = {
                        "error": [video_title, video_id, str(e)],
                        "retries": 0
                    }
                    logged_failures.add(video_id)

                    # Immediately append to not_downloaded.jl
                    with jsonlines.open(failed_path, mode='a') as writer:
                        writer.write(failure_record)

        print(f"Finished downloading audio. {downloaded_count} succeeded. Failures logged to {failed_path}")

    @staticmethod
    def pytubefix_from_playlist(url:str, file, nesting_level = 4, source = '', output_path=None, from_date=None, to_date=None, check_for_downloaded=False):
        ''' Takes a URL, a file (should always be __file__). Generates an output path for the data, a jsonlines file containing scraped data and a folder with all audio files. '''
        if not output_path:
            generated_output_path = Pytubefix_Functions.generate_output_path(file, nesting_level)
        else:
            generated_output_path = Path(output_path)
        Pytubefix_Functions.pytubefix_from_playlist_jsonlines(url, generated_output_path, source, from_date=from_date, to_date=to_date)
        Pytubefix_Functions.pytubefix_from_playlist_audio(url, generated_output_path, from_date=from_date, to_date=to_date, check_for_downloaded=check_for_downloaded)
        print(f'The YouTube channel {url} has been fully scraped! \nThe scraped data can be found at {generated_output_path}.')
        return generated_output_path

    @staticmethod
    def pytubefix_from_single(url:str, file, nesting_level = 4, source = '', output_path=None, from_date=None, to_date=None):
        ''' Takes a URL, a file (should always be __file__). Generates an output path for the data, a jsonlines file containing scraped data and a folder with all audio files. '''
        if not output_path:
            generated_output_path = Pytubefix_Functions.generate_output_path(file, nesting_level)
        else:
            generated_output_path = Path(output_path)

        video = YouTube(url, use_oauth=True, allow_oauth_cache=True)
        generated_output_path.mkdir(parents=True, exist_ok=True)
        jsonlines_path = generated_output_path / 'videos.jl'

        if not source:
            source = Pytubefix_Functions.extract_source(url)

        timestamp = datetime.now().strftime('%Y-%m-%d')
        existing_videos = set()

        if jsonlines_path.exists():
            with jsonlines_path.open('r', encoding='utf-8') as f:
                for line in f:
                    existing_videos.add(json.loads(line)['video_link'])

        if video.watch_url in existing_videos:
            print(f"Already downloaded, skipping: {video.watch_url}")
            return

        print(f"Starting to scrape video...")

        try:
            if video.publish_date: # check if publish date is available (returns None otherwise)
                pub_date = video.publish_date.date()
                if from_date and pub_date < from_date:
                    print(f"Encountered video older than from_date, stopping further scraping.")
                    return
                if to_date and pub_date > to_date:
                    print(f"Skipping: {video.title} — newer than to_date")
                    return

                pub_date_write = video.publish_date.isoformat() # date to write to data

            else: # set missing date value ("") if date not available
                print(f"Not possible to retrieve publish date from {video.title} — set as missing/empty string")
                pub_date_write = ""

            video_data = {
                'scrape_date': timestamp,
                'video_title': video.title,
                'source': source,
                'publication_date': pub_date_write,
                'video_link': video.watch_url,
                'video_id': video.video_id,
            }

            print(f"Scraped: {video.title}")

        except Exception as e:
            print(f"Failed to process '{video.title}'. Error: {e}")

        # Write metadata to file
        video_data_list = [video_data]

        with jsonlines.open(jsonlines_path, mode='a') as writer:
            writer.write_all(video_data_list)
        print(f"💾 Video data written to disk.")

        # Download audio
        m4a_folder_path = generated_output_path / 'm4a_files'
        m4a_folder_path.mkdir(parents=True, exist_ok=True)
        failed_path = generated_output_path / 'not_downloaded.jl'

        # Track video_ids we've already logged as failed to avoid duplication
        logged_failures = set()

        # Load previously failed attempts into memory
        if failed_path.exists():
            with jsonlines.open(failed_path, mode='r') as reader:
                for item in reader:
                    try:
                        title, video_id, _ = item["error"]
                        logged_failures.add(video_id)
                    except Exception as e:
                        print(f"Skipping malformed failure entry: {item} — {e}")

        video_title = video.title
        video_id = video.video_id
        file_name = f"{video_id}.m4a"
        file_path = m4a_folder_path / file_name

        if file_path.exists():
            print(f"Already downloaded, skipping: {video_title}")
            return

        try:
            audio_stream = video.streams.filter(only_audio=True).first()
            if audio_stream is None:
                raise ValueError("No audio stream available.")

            audio_stream.download(output_path=m4a_folder_path, filename=file_name)
            print(f"✅ Finished! Downloaded audio: {video_title}")

        except Exception as e:
            print(f"Failed to download '{video_title}': {e}")

            if video_id not in logged_failures:
                failure_record = {
                    "error": [video_title, video_id, str(e)],
                    "retries": 0
                }
                logged_failures.add(video_id)

                # Immediately append to not_downloaded.jl
                with jsonlines.open(failed_path, mode='a') as writer:
                    writer.write(failure_record)
            
    # version: 2025-10-14
    @staticmethod
    def pytubefix_from_single_v2(url:str, file, nesting_level = 4, source = '', output_path=None, from_date=None, to_date=None):
        ''' Takes a URL, a file (should always be __file__). Generates an output path for the data, a jsonlines file containing scraped data and a folder with all audio files. '''
        if not output_path:
            generated_output_path = Pytubefix_Functions.generate_output_path(file, nesting_level)
        else:
            generated_output_path = Path(output_path)

        # try:
        #     video = YouTube(url, use_oauth=True, allow_oauth_cache=True)
        # except Exception:
        #     # If OAuth flow fails or prompts in a non-interactive environment, fall back
        #     video = YouTube(url, use_oauth=False)

        video = YouTube(url, use_oauth=True, allow_oauth_cache=True)
        
        generated_output_path.mkdir(parents=True, exist_ok=True)
        jsonlines_path = generated_output_path / 'videos.jl'
        if not source:
            source = Pytubefix_Functions.extract_source(url)
        timestamp = datetime.now().strftime('%Y-%m-%d')
        existing_videos = set()
        if jsonlines_path.exists():
            with jsonlines_path.open('r', encoding='utf-8') as f:
                for line in f:
                    existing_videos.add(json.loads(line)['video_link'])
        if video.watch_url in existing_videos:
            print(f"Already downloaded, skipping: {video.watch_url}")
            return

        # 1) Check availability up front and skip early for private/unavailable videos
        try:
            video.check_availability()
        except (ptfx_exc.VideoPrivate, ptfx_exc.VideoUnavailable, ptfx_exc.AgeRestrictedError) as e:
            print(f"Skipping (unavailable/private): {url} — {e}")
            return
        except Exception as e:
            # If anything unexpected happens here, skip safely
            print(f"Skipping (unexpected availability issue) {url}: {e}")
            return

        print("Starting to scrape video...")

        try:
            # Safely get publish date filters
            if getattr(video, "publish_date", None):
                pub_date = video.publish_date.date()
                if from_date and pub_date < from_date:
                    print("Encountered video older than from_date, stopping further scraping.")
                    return
                if to_date and pub_date > to_date:
                    # We *skip* just this one and continue with the rest
                    print(f"Skipping: newer than to_date — {url}")
                    return
                pub_date_write = video.publish_date.isoformat()
            else:
                print("Not possible to retrieve publish date — set as missing/empty string")
                pub_date_write = ""

            # Safely get title (now that availability was checked, this should be fine)
            try:
                video_title = video.title
            except Exception:
                video_title = "(unknown title)"

            video_data = {
                'scrape_date': timestamp,
                'video_title': video_title,
                'source': source,
                'publication_date': pub_date_write,
                'video_link': video.watch_url,
                'video_id': video.video_id,
            }
            print(f"Scraped: {video_title}")

        except Exception as e:
            # IMPORTANT: don't access video.title here; it might re-trigger availability checks
            print(f"Failed to process metadata for {url}. Error: {e}")
            return

        # Write metadata to file
        try:
            with jsonlines.open(jsonlines_path, mode='a') as writer:
                writer.write_all([video_data])
            print("💾 Video data written to disk.")
        except Exception as e:
            print(f"Failed writing metadata for {url}: {e}")
            return

        # Download audio
        m4a_folder_path = generated_output_path / 'm4a_files'
        m4a_folder_path.mkdir(parents=True, exist_ok=True)
        failed_path = generated_output_path / 'not_downloaded.jl'

        logged_failures = set()
        if failed_path.exists():
            with jsonlines.open(failed_path, mode='r') as reader:
                for item in reader:
                    try:
                        title, video_id_failed, _ = item["error"]
                        logged_failures.add(video_id_failed)
                    except Exception as e:
                        print(f"Skipping malformed failure entry: {item} — {e}")

        video_id = video.video_id
        file_name = f"{video_id}.m4a"
        file_path = m4a_folder_path / file_name
        if file_path.exists():
            print(f"Already downloaded, skipping: {video_data.get('video_title','(unknown title)')}")
            return

        try:
            audio_stream = video.streams.filter(only_audio=True).first()
            if audio_stream is None:
                raise ValueError("No audio stream available.")
            audio_stream.download(output_path=m4a_folder_path, filename=file_name)
            print(f"✅ Finished! Downloaded audio: {video_data.get('video_title','(unknown title)')}")
        except Exception as e:
            print(f"Failed to download audio for {url}: {e}")
            if video_id not in logged_failures:
                failure_record = {"error": [video_data.get('video_title','(unknown title)'), video_id, str(e)], "retries": 0}
                logged_failures.add(video_id)
                with jsonlines.open(failed_path, mode='a') as writer:
                    writer.write(failure_record)
