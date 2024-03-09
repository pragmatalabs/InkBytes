"""
---
Author: Julian Delarosa
Email: juliandelarosa@icloud.com
Date: 2023-07-14
Version: 1.0
Description: >
    This is the main file of the URI Harvest program. It is used to scrape news from various sources,
    including local files, shared files, URIs, URLs, and Agent Mode.
Language: Python 3.10
---
"""
import concurrent
import logging
import os
import newspaper
from bs4 import BeautifulSoup
from tinydb import Query

#from inkbytes.common import sysdictionary
from inkbytes.common.system.module_handler import get_module_name
from inkbytes.common.system.utils import generate_threshold_timestamp
from inkbytes.database.tinydb.DataHandler import DataHandler
from inkbytes.models.articles import Article, ArticleBuilder, ArticleCollection
from inkbytes.models.newspaperbase import NewsPaper
from inkbytes.models.outlets import OutletsSource
from scraping.scraper import ScrapingSession, ScrapingStats

MODULE_NAME = get_module_name(2)


class ScraperPool:
    """

    :class: ScrapperPool

    The `ScrapperPool` class is responsible for scraping articles from a given `outlet`. It utilizes a thread pool executor to parallelize the scraping process.

    :param outlet: The source outlet to scrape articles from.
    :type outlet: SourceOutlet

    :param num_workers: The number of worker threads to use in the thread pool. Default is 4.
    :type num_workers: int

    :ivar num_workers: The number of worker threads in the thread pool.
    :ivar logger: The logger instance used for logging.
    :ivar outlet: The source outlet to scrape articles from.

    :Example:
        >>> outlet = SourceOutlet(name="ExampleOutlet")
        >>> scrapper_pool = ScraperPool(outlet)
        >>> scrapper_pool.scrape_outlet()
    """

    def __init__(self, outlet: OutletsSource, agent: str = "", headers: str = "", num_workers: int = 4):
        self.num_workers = num_workers
        self.logger = logging.getLogger(self.__class__.__name__)
        self.outlet = outlet
        self.session = None
        self.agent=agent
        self.headers=headers
        self.scrape_outlet()

    def scrape_outlet(self):
        self.session = ScrapingSession()
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            self.logger.info(f"Scraping articles from: {self.outlet.name}")
            try:
                newsPaper = NewsPaper(agent=self.agent, headers=self.headers)
                NewsScraper(self.outlet, newsPaper, executor, session=self.session)
            except ValueError as e:
                self.logger.error(f"Loading articles from: {self.outlet.name} failed with error: {e}")
                return


def validate_outlet_url(outlet):
    """
    :param outlet: The Outlet object containing the URL to be validated.
    :return: True if the URL is valid and not empty after removing any leading/trailing whitespace, False otherwise.
    """
    return outlet.url and outlet.url.strip()


def process_found_articles(executor, outlet, paper):
    """
    Process articles from a newspaper.

    :param executor: The executor to submit tasks to.
    :type executor: Executor

    :param outlet: The outlet to scrape articles from.
    :type outlet: Outlet

    :param paper: The newspaper containing the articles to be processed.
    :type paper: Paper

    :return: A list of submitted tasks for scraping outlet articles if there are articles in the newspaper. Otherwise, an empty list.
    :rtype: list[Future]
    """
    if len(paper.articles) > 0:
        return [executor.submit(scrape_outlet_article, article, outlet.name) for article in paper.articles]
    else:
        return []


class NewsScraper:
    """
    This class is responsible for scraping news articles from a given news outlet.
    """

    def __init__(self, outlet: OutletsSource, paper: NewsPaper, executor: object, session: ScrapingSession = None):
        self.newspaper = paper
        self.processed_articles = ArticleCollection()
        self.outlet = outlet
        self.executor = executor
        self.logger = logging.getLogger(self.__class__.__name__)
        self.stats = ScrapingStats()
        self.session = session
        self.scrape_news_outlet(self.executor, self.outlet)

    def scrape_news_outlet(self, executor, outlet) -> ScrapingSession:
        """
        :param executor: The executor object responsible for executing the scraping process.
        :param outlet: The news outlet object containing information about the outlet to be scraped.
        :return: None

        This method scrapes articles from the given news outlet using the provided executor object. It updates the outlet name in the session, validates the outlet URL, builds the newspaper object
        *, logs the number of articles found, processes the articles using the executor, logs the number of processed articles, and then processes the outlet articles. If any errors occur during
        * the process, a ValueError will be raised and logged. Finally, the session is completed.
        """
        try:
            self.session.outlet_name = outlet.name
            if validate_outlet_url(outlet):
                paper = self.build_paper_from_outlet(outlet)
                results = process_found_articles(executor, outlet, paper)
                self.logger.info(f"Processing {len(results)} articles for {outlet.name}")
                self.session.total_articles = len(results)
                self.process_outlet_articles(outlet.name, results)
        except ValueError as e:
            self.logger.error(f"Error {e} scraping article from: {outlet}")
        finally:
            self.session.complete_session()

    def build_paper_from_outlet(self, outlet):
        """
        :param outlet: The outlet where the newspaper will be built. This could be a file path, a file-like object, or any other valid output destination.
        :return: The built newspaper as a string.
        """
        self.newspaper.build(outlet)
        return self.newspaper.paper

    def log_foundarticles_count(self, count, outlet):
        """
        Logs the count of articles being processed for a given outlet.

        :param count: The number of articles being processed.
        :param outlet: The outlet for which the articles are being processed.
        :return: None
        """
        self.logger.info(f"Processing {count} articles for {outlet.name}")

    def process_outlet_articles(self, outletBrand: str, results):
        """Process outlet articles.

        This method processes a list of outlet articles and inserts them into the database if they do not already exist.

        Args:
            outletBrand (str): The brand of the outlet.
            results (list): A list of futures representing the articles to be processed.

        Returns:
            None

        Raises:
            None
        """

        time_stamp = generate_threshold_timestamp(15)
        self.session.set_results_staging_file_name(str(time_stamp) + outletBrand + ".db.json")
        data_handler = DataHandler(os.getenv("STAGING_STORAGE_LOCAL")
                                   + self.session.results_staging_file_name)
        self.logger.info(f"Processing {len(results)} articles")
        for future in concurrent.futures.as_completed(results):
            try:
                # Get the article record from the completed future
                record = future.result()
                # Check if a valid record is obtained
                if record:
                    # Check if the article already exists in the database
                    if article_exists(record, data_handler):
                        self.logger.warning(
                            f"{record.id} : Article {record.title[0:20]} already exists: {record.id} @ {outletBrand}")
                        self.session.increment_failed_articles()
                        continue
                    else:
                        # Increment the total article count and add to processed_articles list
                        self.processed_articles.append(record)
                        self.session.increment_successful_articles()
                        self.logger.info(f"{record.id} : Article {record.title[0:20]}.. inserted in : {outletBrand}")
            except Exception as e:
                # Handle exceptions during processing, log the error, and increment failed_articles count
                self.session.increment_failed_articles()
                self.logger.error(f"Error {e} scraping article from: {outletBrand}")
        if self.processed_articles:
            # Insert successfully processed articles into the database
            self.logger.info(f"saving {len(self.processed_articles)} articles from {outletBrand} to database")
            data_handler.insert_multiple(self.processed_articles)


def article_exists(article: Article, data_handler: DataHandler) -> bool:
    """
    Check if an article exists in the given database.

    :param article: The article object to check.
    :param data_handler: The data handler object that provides access to the database.
    :return: True if the article exists in the database, False otherwise.
    """
    result = False
    _article = Query()
    try:
        existing_articles = data_handler.db.search((_article.id == article.id))
        return bool(existing_articles)
    except ValueError as e:
        logging.getLogger().error(f"Error checking if article exists: {e}")
        return result


def pre_process_article(article: newspaper.Article) -> Article:
    """
    Process an article by downloading and parsing it, handling any errors, and performing NLP on it.

    :param article: The article to be processed.
    :type article: newspaper.article.Article
    :return: None
    :rtype: None
    """
    try:
        download_and_parse_article(article)
        perform_nlp_on_article(article)
        return article
    except ValueError as e:
        handle_error_in_article_processing(article, e)


def download_and_parse_article(article: newspaper.Article) -> None:
    """
    Download and parse an article.

    :param article: An instance of `newspaper.article.Article`.
    :return: None
    """
    try:
        article.download()
        article.parse()
    except newspaper.ArticleException as e:
        print(e)
        handle_error_in_article_processing(article, e)


def handle_error_in_article_processing(article: newspaper.Article, error: ValueError) -> None:
    """
    Handle error in article processing.

    :param article: The article to process.
    :param error: The error that occurred during processing.
    :return: None
    """
    logging.getLogger().error(f"Error processing article: {str(error)}")
    _article_html = BeautifulSoup(article.html, 'html.parser')
    article.text = _article_html.get_text()
    article.html = _article_html.prettify()
    article.parse()


def perform_nlp_on_article(article: newspaper.Article) -> None:
    """

    """
    article.nlp()


def build_newspaper_article(article: newspaper.Article) -> newspaper.Article:
    """
    Build a newspaper article based on the provided article object.

    :param article: The article object.
    :type article: newspaper.article.Article
    :return: The built newspaper article.
    :rtype: newspaper.Article
    """
    article = pre_process_article(article)
    # Check if the article was successfully downloaded, parsed, and meets length criteria
    if article.is_parsed and len(article.text) > 10 and article.text:
        return article


def extract_metadata_category(data, fields=['tag', 'section', 'category']):
    """
    Extracts the value of the first existing field from a list of possible field names
    within the 'article' or 'metadata' sections of a JSON structure.

    Args:
    - data (dict): The JSON data as a Python dictionary.
    - fields (list): A list of strings representing the possible field names to search for.

    Returns:
    - str: The value of the first existing field found; otherwise, returns an empty string if none are found.
    """
    # Attempt to find and return the value for the first field that exists
    for section in ['og', 'article', 'metadata', 'fb', 'twitter']:
        metadata = data.get(section, {})
        for field in fields:
            if field in metadata:
                return metadata[field]

    # Return an empty string if none of the fields are found
    return ""


def unify_keywords(article: Article) -> list[str]:
    """
    Extracts and unifies keywords from the root and metadata sections of a JSON object.

    Args:
    - data (dict): The JSON data as a Python dictionary.

    Returns:
    - List[str]: A list of combined and deduplicated keywords.
    """
    # Extract keywords from the root and metadata
    root_keywords = article.keywords
    meta_keywords = article.metadata.get('keywords', '')

    # Convert meta_keywords string to list, assuming keywords are separated by commas
    meta_keywords_list = [keyword.strip() for keyword in meta_keywords.split(',')]

    # Merge and deduplicate keywords
    combined_keywords = list(set(root_keywords + meta_keywords_list))

    # Optionally, process the keywords (e.g., lowercase, remove special characters)
    # This example will just return the combined list
    article.keywords = combined_keywords
    return article


def create_article_record(article: newspaper.Article, newsPaperBrand: str) -> Article:
    """
    Creates an article record from the given article and newspaper brand.

    :param article: A newspaper.article.Article object representing the article.
    :param newsPaperBrand: A string representing the newspaper brand.
    :return: An Article object representing the processed article record.
    """
    articleBuilder = ArticleBuilder()
    articleRecord = articleBuilder.buildFromNewspaper3K(article, newsPaperBrand)
    if articleRecord:
        articleRecord.extract_category()
        articleRecord.article_source = newsPaperBrand
        processedArticle = unify_keywords(articleRecord)
        additional_categories = extract_metadata_category(processedArticle.metadata)
        if len(additional_categories) > 0:
            processedArticle.category = f"{processedArticle.category},{additional_categories.split(', ')}"
            print(f"Adding additional categories {processedArticle.category} ")
    return processedArticle


def scrape_outlet_article(article: newspaper.Article, newsPaperBrand: str) -> Article:
    """
    :param article: The article object to scrape.
    :param newsPaperBrand: The name of the newspaper brand.

    :return: An Article object containing the scraped article data.

    """
    try:
        newspaperArticle = build_newspaper_article(article)
        if len(newspaperArticle.text) > 10:
            return create_article_record(newspaperArticle, newsPaperBrand)
    except ValueError as e:
        logging.getLogger().error(f"Error processing article: {str(e)}")
