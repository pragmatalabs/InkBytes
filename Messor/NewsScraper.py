"""
Author: Julian Delarosa (juliandelarosa@icloud.com)
Date: 2023-07-14
Version: 1.0
Description:
    This is the main file of the URI Harvest program. It is used to scrape news from various sources, including local files,
    shared files, URIs, URLs, and Agent Mode.
System: Messor News Harvest v1.0
Language: Python 3.10
License: MIT License
"""
import concurrent
import newspaper
from bs4 import BeautifulSoup
from tinydb import Query
import time
import calendar
import Logger
import SysDictionary
from Articles import Article, ArticleBuilder, ArticleCollection
from DataHandler import DataHandler
from NewsPapers import NewsPaper
from Outlets import OutletsSource
from Scrapper import ScrapingSession, ScrapingStats

MODULE_NAME = "InkPills Scraper Downloader"
__name__ = MODULE_NAME
logger = Logger.get_logger(MODULE_NAME)


class ScrapperPool:
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
        >>> scrapper_pool = ScrapperPool(outlet)
        >>> scrapper_pool.scrape_outlet()
    """

    def __init__(self, outlet: OutletsSource, num_workers: int = 4):
        self.num_workers = num_workers
        self.logger = logger
        self.outlet = outlet
        self.session = None
        self.scrape_outlet()

    def scrape_outlet(self):
        self.session = ScrapingSession()
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            self.logger.info(f"Scraping articles from: {self.outlet.name}")
            try:
                newsPaper = NewsPaper(agent=SysDictionary.DEFAULT_AGENT, headers=SysDictionary.DEFAULT_HEADER)
                NewsScraper(self.outlet, newsPaper, executor, session=self.session)
            except ValueError as e:
                logger.error(f"Loading articles from: {self.outlet.name} failed with error: {e}")
                return


class NewsScraper:
    """
    This class is responsible for scraping news articles from a given news outlet.
    """

    def __init__(self, outlet: OutletsSource, paper: NewsPaper, executor: object, session: ScrapingSession = None):
        self.paper = paper
        self.processed_articles = ArticleCollection()
        self.outlet = outlet
        self.executor = executor
        self.logger = logger
        self.stats = ScrapingStats()
        self.session = session
        self.scrape_news_outlet(self.executor, self.outlet)

    def scrape_news_outlet(self, executor, outlet) -> ScrapingSession:
        """
        :param executor: The executor object responsible for executing the scraping process.
        :param outlet: The news outlet object containing information about the outlet to be scraped.
        :return: None

        This method scrapes articles from the given news outlet using the provided executor object. It updates the outlet name in the session, validates the outlet URL, builds the paper object
        *, logs the number of articles found, processes the articles using the executor, logs the number of processed articles, and then processes the outlet articles. If any errors occur during
        * the process, a ValueError will be raised and logged. Finally, the session is completed.
        """
        try:
            self.session.outlet_name = outlet.name
            if self.validate_outlet_url(outlet):
                paper = self.build_paper(outlet)
                # self.log_article_count(len(paper.articles), outlet)
                results = self.process_articles(executor, outlet, paper)
                self.logger.info(f"Processing {len(results)} articles for {outlet.name}")
                self.session.total_articles = len(results)
                self.process_outlet_articles(outlet.name, results)
        except ValueError as e:
            self.logger.error(f"Error {e} scraping article from: {outlet}")
        finally:
            self.session.complete_session()

    def validate_outlet_url(self, outlet):
        """
        :param outlet: The Outlet object containing the URL to be validated.
        :return: True if the URL is valid and not empty after removing any leading/trailing whitespace, False otherwise.
        """
        return outlet.url and outlet.url.strip()

    def build_paper(self, outlet):
        """
        :param outlet: The outlet where the paper will be built. This could be a file path, a file-like object, or any other valid output destination.
        :return: The built paper as a string.
        """
        self.paper.build(outlet)
        return self.paper.paper

    def log_article_count(self, count, outlet):
        """
        Logs the count of articles being processed for a given outlet.

        :param count: The number of articles being processed.
        :param outlet: The outlet for which the articles are being processed.
        :return: None
        """
        self.logger.info(f"Processing {count} articles for {outlet.name}")

    def process_articles(self, executor, outlet, paper):
        """
        Process articles from a paper.

        :param executor: The executor to submit tasks to.
        :type executor: Executor

        :param outlet: The outlet to scrape articles from.
        :type outlet: Outlet

        :param paper: The paper containing the articles to be processed.
        :type paper: Paper

        :return: A list of submitted tasks for scraping outlet articles if there are articles in the paper. Otherwise, an empty list.
        :rtype: list[Future]
        """
        if len(paper.articles) > 0:
            return [executor.submit(scrape_outlet_article, article, outlet.name) for article in paper.articles]
        else:
            return []

    def process_outlet_articles(self, outletBrand: str, results):
        """

        :param outletBrand:
        :param results:
        :return:
        """

        current_GMT = time.gmtime()
        time_stamp = calendar.timegm(current_GMT)
        data_handler = DataHandler(SysDictionary.storage_path + str(time_stamp) + outletBrand + ".db.json")
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
                        logger.info(f"{record.id} : Article {record.title[0:20]}.. inserted in : {outletBrand}")
            except Exception as e:
                # Handle exceptions during processing, log the error, and increment failed_articles count
                self.session.increment_failed_articles()
                logger.error(f"Error {e} scraping article from: {outletBrand}")
        if self.processed_articles:
            # Insert successfully processed articles into the database
            logger.info(f"saving {len(self.processed_articles)} articles from {outletBrand} to database")
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
        logger.error(f"Error checking if article exists: {e}")
        return result


def process_article(article: newspaper.Article) -> Article:
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
    logger.error(f"Error processing article: {str(error)}")
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
    article = process_article(article)
    # Check if the article was successfully downloaded, parsed, and meets length criteria
    if article.is_parsed and len(article.text) > 10 and article.text:
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
        processedArticle = articleRecord
        processedArticle.extract_category()
        processedArticle.article_source = newsPaperBrand
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
        logger.error(f"Error processing article: {str(e)}")



