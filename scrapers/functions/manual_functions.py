import csv
import json
import os

import pandas as pd
from os.path import join
from pathlib import Path
import re

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














    @staticmethod
    def standartize_dataset(source, source_entry_given): 

        '''Standartize json lines dataset. Keys have to have a specific order. Also author cant be "none" "no author", but has to have a None value. also other_it, article_cat, and embedded_med_link cant be "none", "nothing else" or []. They must have None as value.'''

        #STEP 1) Read dataset and set up standart item order. If entry not found, add it with 'null' value. Author with value "None" or "no author" needs to have None value
        desired_key_order = ['scrape_date', 'source', 'article_link', 'article_title', 'publication_date', 'author', 
        'article_categories', 'article_text', 'image_links', 'embedded_media_links', 'links_in_text', 'other_items', 'article_HTML', 'mediatype']


        


        stuff_to_be_replaced = {"none", "null", "nothing else"}
        author_that_needs_replacement = {"no author"}

        dataset = Path(source)

        if not dataset.exists(): 
            raise FileNotFoundError(f"Path {source} does not exist")

        #READ the dataset:
        data = dataset.read_text(encoding="utf-8").strip()
        json_lines = [j.strip() for j in data.split("\n") if j.strip()] #reading the given json line

        articles_standartized = []

        #helper functions 
        def values_to_be_changed(value, none_words): #Checking wether entry has "none" "nothing else" "null"

                if not isinstance(value, str): #If the value of an entry is not a string, we return false
                    return False
                else:
                    value = value.strip().lower() #if value is a string remove space, and make it lower
                    return value in none_words  #check if the word is in the defined set, and if yes return True or False

        def set_value_to_none(article, key, incorrect_words): #Fix article_categories, embedded_media_links, other_items
            v = article.get(key)

            if values_to_be_changed(value=v, none_words=incorrect_words):
                article[key] = None

        #Helper function for mediatype

        def media(article):
            types = ["SPIDER.jl", "YT.jl", "TELEGRAM.jl"]
            for n in types:
                if source.endswith(n):
                    article["mediatype"] = n.lower()[:-3]
                    return article

        #Looping through the lines
        for line_number, line in enumerate(json_lines, start=1):
            try:
                article = json.loads(line)

            except json.JSONDecodeError as err:
                raise ValueError(f"Invalid JSON line in {dataset} : {err}")

            for key in desired_key_order: #adding keys that are not present from desired key order in article with None value 
                article.setdefault(key, None)


            #Add media type:

            media(article)

            #Apply to author
            author = article.get("author")
            publication_date = article.get("publication_date")
            if values_to_be_changed(author, author_that_needs_replacement) :
                article["author"] = None
            if values_to_be_changed(publication_date, stuff_to_be_replaced ):
                article["publication_date"] = None

            article_source = article.get("source")
            if article_source:
                article["source"] = source_entry_given
            
            #Change external_links to links_in text
            external_links = article.pop('external_links', None) #return None value if key does not exist
            if external_links:
                article["links_in_text"] = external_links


            #Apply to article_categories, other_item, embedded_media:links
            set_value_to_none(article, "other_items", stuff_to_be_replaced)
            set_value_to_none(article, "article_categories", stuff_to_be_replaced)
            set_value_to_none(article, "embedded_media_links", stuff_to_be_replaced)
            set_value_to_none(article, "links_in_text", stuff_to_be_replaced)

       
            # Reorder and save given file
            reordered_article = {key: article[key] for key in desired_key_order}
            articles_standartized.append(reordered_article)
        
        with dataset.open("w", encoding="utf-8") as f: #save it as it was - get rid of the list [] arround it
            for article in articles_standartized:
                f.write(json.dumps(article, ensure_ascii=False))
                f.write("\n")   
        
        #new_name = dataset.with_name(dataset.name + "standartized")
        #os.rename(dataset, new_name)
    
    
    
    
    
    @staticmethod
    def mediatype_for_tel_and_yt(dir_path): #THIS IS FOR TELEGRAM + YT FOLERS
    
        #Folderpath
        directory_path = Path(dir_path)

        if not directory_path.exists(): 
            raise FileNotFoundError(f"Path {directory_path} does not exist")

    


        for file_path in directory_path.glob("*.jl"):
            filename = file_path.name.lower()

            if filename.endswith("yt.jl"):
                mediatype = "youtube"
            elif filename.endswith("telegram.jl"):
                mediatype = "telegram"
            else:
                continue ##SKIP OVER SPIDERS - THEY are done already

            #READ the dataset:
            data = file_path.read_text(encoding="utf-8").strip()
            json_lines = [j.strip() for j in data.split("\n") if j.strip()] 
            articles_standartized = []


            #Loop through all files
            for line_number, line in enumerate(json_lines, start=1):
                try:
                    article = json.loads(line)

                except json.JSONDecodeError as err:
                    raise ValueError(f"Invalid JSON line in {line_number} : {err}")

                article["mediatype"] = mediatype
                articles_standartized.append(json.dumps(article, ensure_ascii=False))
            
            #Save
            file_path.write_text("\n".join(articles_standartized) + "\n", encoding="utf-8")