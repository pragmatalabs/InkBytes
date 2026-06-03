import re
import string

import nltk
from bs4 import BeautifulSoup
from nltk.corpus import stopwords

__name__ = "TextProcessor"
import logging
logger = logging.getLogger(__name__)
nltk.download('punkt')

class TextProcessor:
    def __init__(self, stemmer, stop_words, language="english"):
        self.stop_words = set(stop_words.words(language))
        self.porter_stemmer = stemmer

    def remove_punctuations(self, txt, punct=string.punctuation):
        """
        This function removes punctuations from the input text.
        """
        return "".join([c for c in txt if c not in punct])

    def remove_stopwords(self, txt, sw=None):
        """
        This function removes the stopwords from the input text.
        """
        if sw is None:
            sw = set(stopwords.words("english"))
        return " ".join([w for w in txt.split() if w.lower() not in sw])

    def purify_text(self, txt):
        """
        This function cleans the text by removing specific line feed characters like '\n', '\r', and '\'.
        """

        soup = BeautifulSoup(txt, "html.parser")
        text = soup.get_text()
        text = self.remove_media_labels(text)
        text = self.remove_non_news_info(text)
        text.replace("\n", " ").replace("\r", " ").replace("\\", " ")
        return text

    def remove_media_labels(self, txt):
        # Define the regex to remove specific media labels
        regex = re.compile(
            r'\["Source: CNN",\s*"See Full Web Article",\s*"via REUTERS",\s*"Our Standards: The Thomson Reuters Trust Principles.",[^]]*\]+'
        )
        result = regex.sub("", txt)
        # Define a more generic regex to remove remaining media labels
        regex = re.compile(r'\["Source:.*?",\s*".*?",\s*".*?",\s*".*?",[^]]*\]+')
        return regex.sub("", result)

    def remove_non_news_info(self, text):
        # Remove login prompts
        text = re.sub(r"(?i)login(.*?)to save", "", text)
        # Remove follow suggestions
        text = re.sub(r"(?i)follow(.*?)@[\w]+", "", text)
        # Remove source attributions
        text = re.sub(r"(?i)Read more next[:\s]+([\w\s]+)[\s\-–—]+", "", text)
        text = re.sub(r"(?i)source[:\s]+([\w\s]+)[\s\-–—]+", "", text)
        # Remove extra whitespace and newlines
        text = re.sub(r"\s+", " ", text)
        text = text.strip()
        return text

    def clean_text(self, txt):
        """
        This function cleans the text by removing specific line feed characters like '\n', '\r', and '\'.
        Additionally, it removes punctuation, stopwords, and converts the text to lowercase.
        """
        txt = txt.replace("\n", "").replace("\r", "")
        txt = self.remove_punctuations(txt)
        txt = self.remove_stopwords(txt)
        return txt.lower()

    def clean_article(self, user_article, nlp):
        user_article = self.clean_text(user_article)
        user_article = self.process_text(user_article, nlp)
        return user_article

    def process_text(text, nlp):
        doc = nlp(text.lower())
        result = []
        for token in doc:
            if token.text in nlp.Defaults.stop_words:
                continue
            if token.is_punct:
                continue
            if token.lemma_ == "-PRON-":
                continue
            result.append(token.lemma_)
        return " ".join(result)

    def preprocess_text(self, text):
        # Tokenize the text into words
        words = nltk.word_tokenize(text.lower())
        # Remove stop words
        words = [w for w in words if w not in self.stop_words]
        # Stem the remaining words
        if self.porter_stemmer:
            words = [self.porter_stemmer.stem(w) for w in words]
        # Join the words back into a single string
        return " ".join(words)

    def detox_NER(self, articles):
        detoxed_articles = []
        for article in articles:
            try:
                # logger.info(f"Detoxing article: {article['title']}")
                article["entities"] = []
                article["topics"] = []
                article["factual"] = ""
                article["sentiment"] = ""
            except Exception as e:
                logger.error(f"Error processing article: {str(e)}")
                continue
            if len(article["text"]) <= 10:
                logger.info("Article without text will be ignored")
                articles.pop(article)
        print(f"Detoxed {len(articles)} articles")
        return articles

    """
    This function takes a list as input, removes duplicates, and returns a list of unique elements.
    """

    def unique(self, list):
        # insert the list to the set
        list_set = set(list)
        # convert the set to the list
        unique_list = list(list_set)
        return unique_list

    def remove_css(self, html):
        # Remove CSS class attributes
        html = re.sub(r'class\s*=\s*["\'][^"\']*["\']', "", html)

        # Remove style attributes
        html = re.sub(r'style\s*=\s*["\'][^"\']*["\']', "", html)

        return html

    def remove_non_standard_html(self, html):
        # Define the regular expression pattern to match non-standard HTML tags
        pattern = r"<\/?(?!html|head|title|body|h[1-6]|p|a|img|ul|ol|li|blockquote|strong|em|br|hr|table|thead|tbody|tfoot|tr|th|td|div|span)[^>]+?>"

        # Remove non-standard HTML tags
        html = re.sub(pattern, "", html)

        return html

    def clean_html(self, html):
        # Load the HTML into BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        if soup.body:
            # Remove unwanted elements
            remove_tags = ["iframe", "script", "style", "meta", "head", "title"]
            for tag in remove_tags:
                for element in soup.find_all(tag):
                    element.decompose()

            # Retain only the body contents
            body = soup.body.extract()
            # Remove all attributes except href from links
            for link in body.find_all("a"):
                link.attrs = {"href": link.attrs.get("href", "")}

            # Apply inline CSS to all elements
            for element in body.find_all(True):
                element.attrs = {
                    "style": " ".join([f"{k}: {v};" for k, v in element.attrs.items()])
                }

            # Use custom template
            template = """
            <html>
            <head>
            </head>
            <body>
                {body}
            </body>
            </html>
            """

            # Replace the body content in the template
            cleaned_html = template.format(body=str(body))

            # Remove CSS and non-standard HTML
            cleaned_html = self.remove_css(cleaned_html)
            cleaned_html = self.remove_non_standard_html(cleaned_html)

            return cleaned_html
        else:
            return
