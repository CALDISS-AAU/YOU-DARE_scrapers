import csv
import json
import os

import pandas as pd
from os.path import join
from pathlib import Path


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

        if 'reply' in csv_path:
            jl_path = csv_path.rsplit('_',6)[0] + '_reply_TELEGRAM.jl'
        else:
            jl_path = csv_path.rsplit('_',5)[0] + '_post_TELEGRAM.jl'
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



    @staticmethod
    def telegram_to_threads(telegram_source, post_csv_path, replies_csv_path=None, sep=';'):
        ## 1) Read data
        posts_df = pd.read_csv(post_csv_path, sep=sep)
        try:
            replies_df = pd.read_csv(replies_csv_path, sep=sep) if replies_csv_path else None
        except FileNotFoundError:
            replies_df = None
            print(f"There are no replies found for this post")

        threads = []

        ## 2) Set up standart columns we want in both post and replies
        posts_df = posts_df.rename(columns={
            'Display_name': 'Display_name',
            'URL' : 'URL',
            'Timestamp' : 'Timestamp',
            'Message_text' : 'Message_text'})
        if replies_df is not None:
            replies_df.rename(columns={
            'Display_name': 'Display_name', 
            'Timestamp': 'Timestamp',
            'Message_text': 'Message_text'})


        ##3) Build one thread per post
        for row_index, post in posts_df.iterrows():
            single_thread = {   ##This is the outside meta, and the thread_text will contain the post + its comments
                "Thread_text": "",
                "URL": post.get("URL", ""),
                "Timestamp": str(post.get("Timestamp", "")),
                "Display-name": post.get("Display_name", ""), 
                "Source" : telegram_source
            }

            ##4) Add one post at a time to the threads. 
            single_thread["Thread_text"] += f"Post: \n--- \nDisplay_name: {post.get("Display_name")}, \nURL: {post.get("URL", "")}, \nTimestamp: {str(post.get("Timestamp", ""))}\n---, \nPost_text: {post.get("Message_text", "")}\n---"
    

            ##5) Get the replies for this post (trying to match the "Message ID")
            if replies_df is not None:
                post_id = post.get("Message ID")
                post_replies = replies_df[replies_df["Message ID"] == post_id]

                for num, (row_index, reply) in enumerate(post_replies.iterrows(), start=1):
                    single_thread["Thread_text"] += f"\n\n\nComment_{num}\n---: \nDisplay_name: {reply.get("Display_name")}, \nTimestamp: {str(reply.get("Timestamp", ""))} \n---, \nComment_text: {reply.get("Message_text", "")} \n--- \n\n\n"
    
            # 5.1 append all
            threads.append(single_thread)

        # 6) SAVE all posts + delete previous.jl files
        base, _ = os.path.splitext(post_csv_path)

        #DELETE OTHER FILES
        dir_path = Path(post_csv_path).resolve().parent         #find the folder of the post
        matches = list(dir_path.glob('*_TELEGRAM.jl'))          #match all TELEGRAM files and remove them
        for p in matches:
            os.remove(p)

        #SAVE THE NEW FILE
        out_path = base + "_TELEGRAM.jl"
        with open(out_path, "w", encoding="utf-8") as file:
            for object in threads:
                file.write(json.dumps(object, ensure_ascii=False) + "\n")

        print(f"saved {len(threads)} threads to {out_path}")
        return out_path















