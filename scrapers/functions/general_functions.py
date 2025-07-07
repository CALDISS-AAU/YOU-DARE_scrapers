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

    @staticmethod
    def safe_urljoin(base, link):
        parsed = urlparse(link)
        
        if parsed.netloc:  # Already an absolute URL
            # Encode only the path (preserve query, etc.)
            safe_path = quote(parsed.path, safe="/")  # avoid encoding slashes
            return urlunparse(parsed._replace(path=safe_path))
        else:
            # Relative URL — join with base, then re-parse and encode path
            absolute = urljoin(base, link)
            parsed_abs = urlparse(absolute)
            safe_path = quote(parsed_abs.path, safe="/")
            return urlunparse(parsed_abs._replace(path=safe_path))