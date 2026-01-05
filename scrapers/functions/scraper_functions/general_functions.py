import re
from urllib.parse import urljoin, urlparse, urlunparse, quote

class General_Functions:
    @staticmethod # Because it doesn't take any self defined variables
    def clean_text(text: str):
        ''' Takes a string and cleans it for \n, \r, \t and spare spaces '''
        text = re.sub(r'[\n\r\t]+', ' ', text)
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def join_and_clean(list_of_strings: list, join_character = ' '):
        ''' Takes a list of strings, joins them and cleans the resulting string '''
        joined_string = join_character.join(list_of_strings).strip()
        clean_string = General_Functions.clean_text(joined_string)
        return clean_string
