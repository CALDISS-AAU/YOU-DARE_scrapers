# pip install pdfminer.six # 

from pdfminer.high_level import extract_text
from datetime import datetime
import json

input_file = '/work/YOU-DARE/scrapers/data/United_Kingdom/reform_uk/Reform_UK_Our_Contract_with_You.pdf'
output_file = '/work/YOU-DARE/scrapers/data/United_Kingdom/reform_uk/Reform_UK_Our_Contract_with_You.jl'

pdf_text_raw = extract_text(input_file)
pdf_text = pdf_text_raw.replace('\n', ' ')
print(pdf_text)

scrape_date = datetime.now().strftime('%Y-%m-%d')
publication_date = 'None'
source = 'Reform UK'
article_link = 'https://assets.nationbuilder.com/reformuk/pages/253/attachments/original/1718625371/Reform_UK_Our_Contract_with_You.pdf?1718625371'
article_title = 'None'
author = 'None'
article_categories = 'None'
article_text = pdf_text
image_links = 'None'
external_links = 'None'
embedded_media_links = 'None'
other_items = 'None'
article_HTML = 'None'

output = {'scrape_date': scrape_date,
          'publication_date': publication_date,
          'source': source,
          'article_link': article_link,
          'article_title': article_title,
          'author': author,
          'article_categories': article_categories,
          'article_text': article_text,
          'image_links': image_links,
          'external_links': external_links,
          'embedded_media_links': embedded_media_links,
          'other_items': other_items,
          'article_HTML': article_HTML}

with open(output_file, 'w') as of:
    of.write(json.dumps(output))

# # # items['scrape_date'] = timestamp
# # # items['publication_date'] = publication_date
# # # items['source'] = self.source
# # # items['article_link'] = article_link
# # # items['article_title'] = article_title_clean
# # # items['author'] = author_clean
# # # items['article_categories'] = article_categories
# # # items['article_text'] = article_text_clean
# # # items['image_links'] = image_links
# # # items['embedded_media_links'] = embedded_med
# # # items['external_links'] = external_links
# # # items['article_HTML'] = response.get()
# # # items['other_items'] = 'None'