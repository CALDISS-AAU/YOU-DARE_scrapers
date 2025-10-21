def merge_txt_files(file1, file2, output_file):
    with open(file1, "r", encoding="utf-8") as f1, open(file2, "r", encoding="utf-8") as f2:
        lines = f1.readlines() + f2.readlines()

    # Remove duplicates using set
    unique_lines = set(lines)

    # Optional: sort alphabetically
    # unique_lines = sorted(unique_lines)

    with open(output_file, "w", encoding="utf-8") as out:
        out.writelines(unique_lines)


path_1 = 'YOU-DARE/scrapers/data/Hungary/fidesz_videos_SPIDER/data_fidesz_videos_p0-20_SPIDER.txt'
path_2 = 'YOU-DARE/scrapers/data/Hungary/fidesz_videos_SPIDER/data_fidesz_videos_p20-fin_SPIDER.txt'
output_path = 'YOU-DARE/scrapers/data/Hungary/fidesz_videos_SPIDER/data_fidesz_videos_merged_SPIDER.txt'

merge_txt_files(path_1, path_2, output_path)
