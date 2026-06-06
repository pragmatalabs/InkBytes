#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
News scraper module for Messor application.

Combined scraper module for URI Harvest program. Used to scrape news from various sources
including local files, shared files, URIs, URLs, and Agent Mode.
Enhanced with improved category extraction capabilities.

Author: Julian de la Rosa (juliandelarosa@icloud.com)
Version: 2.1
Date: 2025-04-14 (updated)
Copyright: © 2025 InkBytes Technologies
"""
import concurrent.futures
import json
import logging
import os
import re
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

import newspaper
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

# Imports from the original files - kept for compatibility
from inkbytes.common.system.logger.advanced_logger import LogDestination, AdvancedLogger
from inkbytes.common.system.config.config_loader import ConfigLoader
from inkbytes.common.system.module_handler import get_module_name
from inkbytes.common.system.utils import generate_threshold_timestamp, generate_today_timestamp
from inkbytes.models.articles import Article, ArticleBuilder, ArticleCollection
from inkbytes.models.newspaperbase import NewsPaper
from inkbytes.models.outlets import OutletsSource

# v1: TinyDB was retired (INK-5). Per-cycle staging now uses a plain JSON store.
from core.staging_store import StagingStore, article_id_exists_in_file, get_staged_content_hash

# Module setup
MODULE_NAME = get_module_name(2)
logger = logging.getLogger(MODULE_NAME)

# Configuration loading
config = ConfigLoader('./env.yaml')
logger_config = {
    'logger_name': MODULE_NAME,
    'log_level': config.logging.log_level(),
    'log_file': config.logging.log_file(),
    'log_format': config.logging.log_format(),
    'destinations': [LogDestination.FILE.value],
}

advanced_logger = AdvancedLogger(logger_config)


# ===== Models and Enums from scraper.py =====

class SessionSavingMode(Enum):
    SAVE_TO_FILE = "save_to_file"
    SEND_TO_API = "send_to_api"


class JsonEncoderForDateTime(json.JSONEncoder):
    def encodeDatetimeObject(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().encodeDatetimeObject(obj)


class ScrapingStats(BaseModel):
    start_time: datetime = Field(default_factory=datetime.utcnow)
    outlet_name: str = Field(default_factory=str)
    results_staging_file_name: str = Field(default_factory=str)
    end_time: Optional[datetime] = Field(default_factory=datetime.utcnow)
    completed_session: Optional[bool] = False
    successful_articles: int = Field(
        default=0, description="The total number of successful articles processed.")
    total_articles: int = Field(
        default=0, description="The total number of articles processed.")
    failed_articles: int = Field(
        default=0, description="The number of failed articles during processing.")


class ScrapingSession(ScrapingStats):
    # Statistics for duplicate detection
    duplicates_current_batch: int = Field(default=0, description="Number of duplicates in current batch")
    duplicates_previous_scrapes: int = Field(default=0, description="Number of duplicates found in previous scrapes")
    
    def complete_session(self):
        """Mark the session as completed and set the end time."""
        self.end_time = datetime.utcnow()
        self.completed_session = True

    def increment_total_articles(self):
        """Increment the total number of articles."""
        self.total_articles += 1

    def increment_failed_articles(self):
        """Increment the number of failed articles."""
        self.failed_articles += 1

    def increment_successful_articles(self):
        """Increment the number of successful articles."""
        self.successful_articles += 1
        
    def increment_duplicates_current_batch(self):
        """Increment the number of duplicate articles in the current batch."""
        self.duplicates_current_batch += 1
        
    def increment_duplicates_previous_scrapes(self):
        """Increment the number of duplicate articles found in previous scrapes."""
        self.duplicates_previous_scrapes += 1

    def set_results_staging_file_name(self, file_name: str):
        """Set the name of the results staging file."""
        self.results_staging_file_name = file_name

    def calculate_duration(self) -> float:
        """Calculate the duration of the scraping session in seconds."""
        end_time = self.end_time or datetime.utcnow()
        return (end_time - self.start_time).total_seconds()

    def calculate_success_rate(self) -> float:
        """Calculate the success rate of the scraping session."""
        if self.total_articles == 0:
            return 0
        return self.successful_articles / self.total_articles
        
    def calculate_duplicate_rate(self) -> float:
        """Calculate the percentage of articles that were detected as duplicates."""
        if self.total_articles == 0:
            return 0
        total_duplicates = self.duplicates_current_batch + self.duplicates_previous_scrapes
        return (total_duplicates / self.total_articles) * 100

    def to_json(self) -> dict:
        """Convert the session to a JSON-serializable dict."""
        duration = self.calculate_duration()
        success_rate = self.calculate_success_rate()
        duplicate_rate = self.calculate_duplicate_rate()
        
        return {
            "data": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "total_articles": self.total_articles,
                "results_staging_file_name": self.results_staging_file_name,
                "failed_articles": self.failed_articles,
                "successful_articles": self.successful_articles,
                "duplicates_current_batch": self.duplicates_current_batch,
                "duplicates_previous_scrapes": self.duplicates_previous_scrapes,
                "total_duplicates": self.duplicates_current_batch + self.duplicates_previous_scrapes,
                "duration": duration,
                "success_rate": success_rate,
                "duplicate_rate": duplicate_rate,
                "outlet": self.outlet_name,
                "completed_session": self.completed_session
            }
        }

    class Config:
        from_attributes = True


class ScraperResults(BaseModel):
    processed_articles: ArticleCollection
    session: ScrapingSession


# ===== Functions from newsscraper.py =====

def scrape_outlet(outlet, agent, headers, num_workers=2, languages=None) -> ScrapingSession:
    """
    Scrape articles from a given outlet.
    
    This function coordinates the scraping process for a single outlet:
    1. Initializes the newspaper and scraper
    2. Scrapes the outlet
    3. Handles duplicate article detection across sessions
    4. Completes the session with statistics
    
    Args:
        outlet: The news outlet to scrape.
        agent: The user agent to use.
        headers: The headers to use for the request.
        num_workers: Number of concurrent workers.
        languages: List of languages to filter articles by.

    Returns:
        ScrapingSession: The scraping session containing stats.
    """
    if languages is None:
        languages = ['en']
    logger.info(f"Scraping articles from: {outlet.name}")
    session = ScrapingSession()
    try:
        newsPaper = NewsPaper(agent=agent, headers=headers)
    except ValueError as e:
        logger.error(f"Failed to initialize NewsPaper for: {outlet.name} with error: {e}")
        return session

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            newsScraper = NewsScraper(outlet, newsPaper, executor, session=session, languages=languages)
            newsScraper.scrape_news_outlet(executor, outlet)
            
            # At this point, the session should have all information including:
            # - The file path and name
            # - Number of articles processed, successful, and failed
            # - Detailed stats about duplicates
            # The calling ScraperService will use this session to handle S3 upload and RabbitMQ messaging
            
        return newsScraper.session
    except Exception as e:
        logger.error(f"Scraping articles from: {outlet.name} failed with error: {e}")
        return session


def validate_outlet_url(outlet):
    """
    Validate that an outlet URL is not empty.

    Args:
        outlet: The Outlet object containing the URL to be validated.

    Returns:
        bool: True if the URL is valid and not empty.
    """
    return outlet.url and outlet.url.strip()


def process_found_articles(executor, outlet, paper) -> list:
    """
    Process articles found in a newspaper.

    Args:
        executor: The executor to submit tasks to.
        outlet: The outlet being scraped.
        paper: The newspaper object containing articles.

    Returns:
        list: A list of futures for article scraping tasks.
    """
    if len(paper.articles) > 0:
        return [executor.submit(scrape_outlet_article, article, outlet.name) for article in paper.articles]
    else:
        return []


def article_exists(article: Article, store: StagingStore) -> bool:
    """
    Check if an article already exists in the current cycle's staging store.

    Args:
        article: The article to check.
        store: The per-cycle staging store.

    Returns:
        bool: True if the article exists, False otherwise.
    """
    try:
        return bool(article.id) and store.contains(article.id)
    except Exception as e:
        logging.getLogger().error(f"Error checking if article exists: {e}")
        return False


def check_article_exists_in_all_scrapes(article: Article, outlet_name: str) -> bool:
    """
    Check if an article already exists in any scrape file for the given outlet.
    
    Args:
        article: The article to check.
        outlet_name: The name of the outlet.
        
    Returns:
        bool: True if the article exists in any scrape file, False otherwise.
    """
    logger = logging.getLogger()
    try:
        # Get directory where scrapes are stored
        scrapes_dir = config.storage.staging.local.scraping()
        
        if not os.path.exists(scrapes_dir):
            logger.warning(f"Scrapes directory does not exist: {scrapes_dir}")
            return False
            
        # Find all scrape files for this outlet
        outlet_scrape_files = []
        for filename in os.listdir(scrapes_dir):
            if outlet_name in filename and filename.endswith(".db.json"):
                outlet_scrape_files.append(os.path.join(scrapes_dir, filename))
                
        if not outlet_scrape_files:
            logger.debug(f"No existing scrape files found for outlet: {outlet_name}")
            return False
            
        # Log how many files we're checking
        logger.debug(f"Checking {len(outlet_scrape_files)} existing scrape files for outlet: {outlet_name}")
        
        # Check each file for article ID — and compare content if found.
        import hashlib as _hashlib
        article_id    = article.id
        article_title = article.title[:30] if article.title else "Unknown"
        new_hash = _hashlib.md5(
            ((article.title or "") + (article.text or "")).encode("utf-8")
        ).hexdigest()

        for idx, file_path in enumerate(outlet_scrape_files, 1):
            if idx % 5 == 0 or idx == 1 or idx == len(outlet_scrape_files):
                logger.debug(f"Checking file {idx}/{len(outlet_scrape_files)}: {os.path.basename(file_path)}")

            try:
                stored_hash = get_staged_content_hash(file_path, article_id)
                if stored_hash is None:
                    continue  # article not in this file

                if stored_hash == new_hash:
                    # Same URL, same content — genuine duplicate, skip.
                    logger.info(
                        f"Article '{article_title}' (ID: {article_id}) unchanged in "
                        f"{os.path.basename(file_path)} — skipping"
                    )
                    return True

                # Same URL, different content — article has been updated.
                # Allow re-publication so Curator can re-enrich with fresh body.
                logger.info(
                    f"Article '{article_title}' (ID: {article_id}) has updated content "
                    f"vs {os.path.basename(file_path)} — re-publishing"
                )
                return False

            except Exception as e:
                logger.error(f"Error checking scrape file {file_path}: {e}")
                continue

        logger.debug(f"Article '{article_title}' (ID: {article_id}) not found in any existing scrape files for {outlet_name}")
        return False
    except Exception as e:
        logger.error(f"Error checking if article exists in scrape files: {e}")
        return False


def pre_process_article(article: newspaper.Article) -> newspaper.Article:
    """
    Download, parse and run NLP on an article.

    Args:
        article: The newspaper article object.

    Returns:
        newspaper.Article: The processed article, or None if processing failed.
    """
    try:
        article.download()
        article.parse()
        # INK-11: do NOT call article.nlp() here. newspaper3k's .nlp() does
        # heuristic keyword extraction + summary — that's enrichment, which
        # belongs to Curator (Skill 1: ENRICH). Messor stays a pure harvester.
        if article.is_parsed and article.text and article.meta_lang:
            return article
    except ValueError as e:
        handle_error_in_article_processing(article, e)


def scrape_outlet_article(article: newspaper.Article, newsPaperBrand: str) -> Article:
    """
    Scrape a single article from an outlet.

    Args:
        article: The newspaper article to scrape.
        newsPaperBrand: The name of the newspaper brand.

    Returns:
        Article: The scraped article object.
    """
    try:
        newspaperArticle = build_newspaper_article(article)
        if newspaperArticle and len(newspaperArticle.text) > 150:
            return create_article_record(newspaperArticle, newsPaperBrand)
    except ValueError as e:
        logging.getLogger().error(f"Error processing article: {str(e)}")


def extract_metadata_category(data: dict) -> List[str]:
    """
    Extract comprehensive category information from article metadata.

    Args:
        data: The metadata dictionary.

    Returns:
        list: List of unique categories found in metadata.
    """
    # Common metadata sections in news outlets
    sections = [
        'og',                   # Open Graph protocol
        'article',              # Article-specific metadata
        'metadata',             # Generic metadata
        'twitter',              # Twitter card metadata
        'schema',               # Schema.org structured data
        'dublincore',           # Dublin Core metadata
        'pageinfo',             # Page information
        'page',                 # Page data
        'content'               # Content information
    ]

    # Common fields that might contain category information
    fields = [
        'section',              # Primary section
        'category',             # Category
        'tag',                  # Tags
        'keywords',             # Keywords
        'topic',                # Topic
        'subject',              # Subject
        'department',           # Department
        'beat',                 # News beat
        'genre',                # Content genre
        'type',                 # Content type
        'classification',       # Content classification
        'taxonomies',           # Taxonomies
        'primarySection',       # Primary section
        'secondarySection',     # Secondary section
        'contentType',          # Content type
        'subType',              # Content subtype
        'primaryTag',           # Primary tag
        'secondaryTags'         # Secondary tags
    ]

    unique_categories = []

    # Special case: check for structured arrays of categories
    category_arrays = [
        'categories',
        'tags',
        'keywords',
        'topics',
        'sections',
        'taxonomies'
    ]

    # First, look for any top-level arrays of categories
    for array_name in category_arrays:
        if array_name in data:
            categories_array = data[array_name]
            if isinstance(categories_array, list):
                for item in categories_array:
                    # Handle both string items and dictionary items with a name/value field
                    if isinstance(item, str):
                        category = item.strip()
                    elif isinstance(item, dict) and ('name' in item or 'value' in item or 'term' in item):
                        category = item.get('name', item.get('value', item.get('term', ''))).strip()
                    else:
                        continue

                    if category and category not in unique_categories:
                        unique_categories.append(category)

    # Then look through the section/field combinations
    for section in sections:
        metadata = data.get(section, {})

        # Handle both dictionary and nested objects
        if not isinstance(metadata, dict):
            continue

        for field in fields:
            if field in metadata:
                value = metadata[field]

                # Skip if empty
                if not value:
                    continue

                # Handle different value types
                if isinstance(value, str):
                    # Split comma-separated values
                    categories = [cat.strip() for cat in value.split(',')]
                elif isinstance(value, list):
                    # If already a list, process each item
                    categories = []
                    for item in value:
                        if isinstance(item, str):
                            categories.append(item.strip())
                        elif isinstance(item, dict) and ('name' in item or 'value' in item or 'term' in item):
                            category = item.get('name', item.get('value', item.get('term', ''))).strip()
                            if category:
                                categories.append(category)
                elif isinstance(value, dict) and ('name' in value or 'value' in value or 'term' in value):
                    # Handle dictionary with name/value field
                    category = value.get('name', value.get('value', value.get('term', ''))).strip()
                    categories = [category] if category else []
                else:
                    # For other types, convert to string
                    categories = [str(value)]

                # Add non-empty, non-duplicate categories
                for cat in categories:
                    if cat and cat not in unique_categories:
                        unique_categories.append(cat)

    return unique_categories


def extract_html_categories(html: str) -> List[str]:
    """
    Extract categories from the HTML content of a page.

    Args:
        html: HTML content of the page.

    Returns:
        list: List of categories found in HTML.
    """
    categories = []
    try:
        soup = BeautifulSoup(html, 'html.parser')

        # Extract from common category elements
        cat_elements = []

        # Breadcrumbs often contain category information
        breadcrumbs = soup.select('.breadcrumb, .breadcrumbs, nav[aria-label*="breadcrumb"], ol[itemscope][itemtype*="BreadcrumbList"]')
        for crumb in breadcrumbs:
            links = crumb.select('a, span[itemprop="name"]')
            for link in links:
                text = link.get_text().strip()
                if text and text.lower() not in ["home", "homepage", "main", "index"]:
                    cat_elements.append(text)

        # Category labels
        category_labels = soup.select('.category, .tag, .section, a[href*="/category/"], a[href*="/section/"], a[href*="/topic/"]')
        for label in category_labels:
            text = label.get_text().strip()
            if text:
                cat_elements.append(text)

        # Category metatags
        meta_categories = soup.select('meta[property="article:section"], meta[name="category"], meta[name="news_keywords"]')
        for meta in meta_categories:
            content = meta.get('content', '').strip()
            if content:
                for cat in content.split(','):
                    cat_elements.append(cat.strip())

        # Tags
        tags = soup.select('.tags a, .tag-list a, .topics a')
        for tag in tags:
            text = tag.get_text().strip()
            if text:
                cat_elements.append(text)

        # Process and de-duplicate
        for cat in cat_elements:
            # Clean up the category text
            cat = re.sub(r'[^a-zA-Z0-9\s\-]', '', cat).strip()
            if cat and cat not in categories and len(cat) > 1:
                categories.append(cat)
    except Exception as e:
        logger.error(f"Error extracting categories from HTML: {e}")

    return categories


def extract_newspaper_metadata(article: newspaper.Article) -> Dict[str, Any]:
    """
    Extract metadata from a newspaper Article object.

    Args:
        article: A newspaper.Article object.

    Returns:
        dict: A dictionary of metadata.
    """
    metadata = {}

    # Basic metadata
    if hasattr(article, 'meta_data') and article.meta_data:
        metadata['metadata'] = article.meta_data

        # OpenGraph metadata
        metadata['og'] = {}
        for key, value in article.meta_data.items():
            if key.startswith('og:'):
                clean_key = key.replace('og:', '')
                metadata['og'][clean_key] = value

        # Twitter metadata
        metadata['twitter'] = {}
        for key, value in article.meta_data.items():
            if key.startswith('twitter:'):
                clean_key = key.replace('twitter:', '')
                metadata['twitter'][clean_key] = value

        # Article metadata
        metadata['article'] = {}
        for key, value in article.meta_data.items():
            if key.startswith('article:'):
                clean_key = key.replace('article:', '')
                metadata['article'][clean_key] = value

    # Keywords
    if hasattr(article, 'meta_keywords') and article.meta_keywords:
        metadata['keywords'] = list(article.meta_keywords)

    # Tags are sometimes encoded in data attributes
    if hasattr(article, 'meta_data') and article.meta_data:
        for key, value in article.meta_data.items():
            if 'tag' in key.lower() or 'category' in key.lower() or 'topic' in key.lower():
                metadata[key] = value

    return metadata


def extract_url_categories(url: str) -> List[str]:
    """
    Extract potential categories from the URL structure.

    Args:
        url: The URL to extract categories from.

    Returns:
        list: A list of potential categories extracted from the URL.
    """
    categories = []

    try:
        # Remove protocol and domain parts
        parts = url.split('/')
        if len(parts) >= 3:
            path_parts = parts[3:]

            # Common URL path patterns that indicate categories
            category_indicators = ['category', 'section', 'topic', 'department', 'channel']

            for i, part in enumerate(path_parts):
                # Skip common non-category parts
                if part.lower() in ['index.html', 'index.php', 'index', 'story', 'article', 'news', '']:
                    continue

                # Check if this part is a category indicator
                if part.lower() in category_indicators and i + 1 < len(path_parts):
                    # The next part is likely the actual category
                    category = path_parts[i + 1]
                    # Clean it up
                    category = re.sub(r'[^a-zA-Z0-9\s\-]', '', category).strip()
                    if category and len(category) > 1:
                        categories.append(category)

                # Also check parts that might be categories themselves
                # Avoid dates and numeric IDs
                if (not re.match(r'^\d+$', part) and  # Not just digits
                        not re.match(r'^\d{4}$', part) and  # Not a year
                        not re.match(r'^\d{1,2}-\d{1,2}-\d{2,4}$', part) and  # Not a date
                        not part.endswith('.html') and
                        not part.endswith('.php') and
                        len(part) > 1):

                    # Replace hyphens and underscores with spaces
                    category = part.replace('-', ' ').replace('_', ' ')
                    # Clean it up
                    category = re.sub(r'[^a-zA-Z0-9\s]', '', category).strip()

                    if category and len(category) > 1:
                        categories.append(category)
    except Exception as e:
        logger.error(f"Error extracting categories from URL: {e}")

    return categories


def extract_meta_keywords(article: Article) -> List[str]:
    """
    Return raw meta_keywords pulled from the article's HTML metadata.

    INK-11: this used to be `unify_keywords`, which mixed in newspaper3k's
    `.nlp()`-derived keywords. That blended raw harvest data with heuristic
    NLP and is now Curator's job. Messor only forwards the keywords it
    literally saw in the page's `<meta>` tags.
    """
    meta_keywords = article.metadata.get('keywords', '') if article.metadata else ''

    if isinstance(meta_keywords, str):
        items = [k.strip() for k in meta_keywords.split(',')]
    elif isinstance(meta_keywords, list):
        items = meta_keywords
    else:
        items = []

    # Dedup + drop empties, preserve order.
    seen, ordered = set(), []
    for k in items:
        if k and k not in seen:
            seen.add(k)
            ordered.append(k)
    return ordered


def get_comprehensive_categories(article: newspaper.Article, articleRecord: Article) -> List[str]:
    """
    Get comprehensive categories from multiple sources for an article.

    Args:
        article: The newspaper article object.
        articleRecord: The Article record object.

    Returns:
        list: A comprehensive list of categories from all available sources.
    """
    all_categories = []

    # 1. Extract categories from metadata
    metadata = extract_newspaper_metadata(article)
    metadata_categories = extract_metadata_category(metadata)
    all_categories.extend(metadata_categories)

    # 2. Extract categories from HTML content
    if hasattr(article, 'html') and article.html:
        html_categories = extract_html_categories(article.html)
        all_categories.extend(html_categories)

    # 3. Extract categories from URL
    if articleRecord.article_url:
        url_categories = extract_url_categories(articleRecord.article_url)
        all_categories.extend(url_categories)

    # INK-11: removed "extend with article.keywords" — those keywords come
    # from newspaper3k's .nlp() heuristic. Curator computes canonical
    # keywords from the LLM call; Messor only forwards what it literally
    # saw in HTML/meta/URL.

    # De-duplicate categories
    unique_categories = []
    for category in all_categories:
        category = category.strip()
        if category and category not in unique_categories:
            unique_categories.append(category)

    return unique_categories


def create_article_record(article: newspaper.Article, newsPaperBrand: str) -> Article:
    """
    Create an article record from a newspaper article.

    Args:
        article: The newspaper article.
        newsPaperBrand: The newspaper brand name.

    Returns:
        Article: The created article record.
    """
    articleBuilder = ArticleBuilder()
    articleRecord = articleBuilder.buildFromNewspaper3K(article, newsPaperBrand)

    if articleRecord:
        # Set the article source
        articleRecord.article_source = newsPaperBrand

        # INK-11: keep raw meta keywords only. Canonical keyword list is
        # Curator's job (Skill 1: ENRICH).
        articleRecord.keywords = extract_meta_keywords(articleRecord)

        # Get comprehensive categories from all available sources
        comprehensive_categories = get_comprehensive_categories(article, articleRecord)

        # Only proceed with category processing if we found some categories
        if comprehensive_categories and len(comprehensive_categories) > 0:
            # Store all the categories we found
            articleRecord.meta_categories = comprehensive_categories
            #logger.info(f"Adding additional categories: {articleRecord.meta_categories}")

            # Extract the main category from our list of categories
            main_category = articleRecord.extract_main_category_from_list(comprehensive_categories)
            articleRecord.category = main_category

            # Optionally remove the main category from the additional categories list
            # This prevents duplication if you're displaying both separately
            if main_category in articleRecord.meta_categories:
                articleRecord.meta_categories.remove(main_category)

            logger.info(f"Main category: {articleRecord.category}")
        else:
            # Fallback: If no categories were found, use URL-based extraction
            articleRecord.category = articleRecord.article_url.split("/")[-2] or "general"
            logger.info(f"No categories found. Using URL-based category: {articleRecord.category}")

    return articleRecord


def build_newspaper_article(article: newspaper.Article) -> newspaper.Article:
    """
    Build a newspaper article by processing it.

    Args:
        article: The article to build.

    Returns:
        newspaper.Article: The built article if successful, None otherwise.
    """
    # First pre-process the article
    article = pre_process_article(article)

    # Check if the article was properly parsed and contains text
    if article and article.is_parsed and article.text:
        # Count words instead of characters for a more meaningful content check
        word_count = len(article.text.split())

        # Only accept articles with a substantial number of words
        # 50 words is approximately a short paragraph of meaningful content
        if word_count >= config.scraper.min_word_count():
            return article
        else:
            logger.info(f"Article {article.title} has too few words: {word_count} words")
            return None


def handle_error_in_article_processing(article: newspaper.Article, error: ValueError) -> None:
    """
    Handle errors that occur during article processing.

    Args:
        article: The article being processed.
        error: The error that occurred.
    """
    logging.getLogger().error(f"Error processing article{article.title}: {str(error)}")
    try:
        _article_html = BeautifulSoup(article.html, 'html.parser')
        article.text = _article_html.text
        article.html = _article_html.prettify()
        article.parse()
    except Exception as e:
        logging.getLogger().error(f"Error in error handling for article: {str(e)}")


# ===== NewsScraper class =====

@advanced_logger.log_function
class NewsScraper:
    """
    Class responsible for scraping news articles from a given news outlet.
    """

    def __init__(self, outlet: OutletsSource, paper: NewsPaper, executor: object, session: ScrapingSession = None,
                 languages=None):
        """
        Initialize a NewsScraper instance.

        Args:
            outlet: The outlet to scrape.
            paper: The newspaper object.
            executor: The thread executor.
            session: Optional scraping session for stats tracking.
            languages: List of languages to filter by.
        """
        if languages is None:
            languages = ['en']
        self.newspaper = paper
        self.processed_articles = ArticleCollection()
        self.outlet = outlet
        self.executor = executor
        self.logger = logging.getLogger(self.__class__.__name__)
        self.stats = ScrapingStats()
        self.session = session or ScrapingSession()
        self.languages = languages

    def scrape_news_outlet(self, executor, outlet) -> ScrapingSession:
        """
        Scrape articles from a news outlet.

        Args:
            executor: The executor for concurrent processing.
            outlet: The outlet to scrape.

        Returns:
            ScrapingSession: The scraping session with stats.
        """
        try:
            self.session.outlet_name = outlet.name
            if validate_outlet_url(outlet):
                paper = self.newspaper.build(outlet)
                results = process_found_articles(executor, outlet, paper)
                self.session.total_articles = len(results)

                if len(results) > 0:
                    self.logger.info(f"Saving {len(results)} articles for {outlet.name}")
                    self.process_outlet_articles(outlet.name, results)
                else:
                    self.logger.info(f"No articles could be retrieved from {outlet.name}")
            else:
                self.logger.info(f"Invalid outlet URL {outlet.url}")
        except ValueError as e:
            self.logger.error(f"Error {e} scraping article from: {outlet}")
        finally:
            self.session.complete_session()
            return self.session

    def process_outlet_articles(self, outletBrand: str, results):
        """
        Process articles from an outlet and save them to the database.
        Checks for duplicates not only in the current database but also in previously scraped files.

        Args:
            outletBrand: The brand name of the outlet.
            results: List of article futures to process.
        """
        time_stamp = generate_today_timestamp()
        self.session.set_results_staging_file_name(f"{time_stamp}.{outletBrand}.db.json")
        staging_path = config.storage.staging.local.scraping()
        file_path = os.path.join(staging_path, self.session.results_staging_file_name)
        self.logger.info(f"Saving articles to: {file_path}")
        data_handler = StagingStore(file_path)

        total_articles = len(results)
        processed_count = 0
        duplicates_in_current_batch = 0
        duplicates_in_previous_scrapes = 0
        failed_to_process = 0
        
        self.logger.info(f"Processing {total_articles} articles from {outletBrand}")
        
        # Create progress update function to avoid duplicating log code
        def log_progress():
            progress_pct = (processed_count / total_articles) * 100 if total_articles > 0 else 0
            self.logger.info(
                f"Progress: {processed_count}/{total_articles} ({progress_pct:.1f}%) articles processed | "
                f"New: {len(self.processed_articles)} | "
                f"Duplicates: {duplicates_in_current_batch} (current batch), {duplicates_in_previous_scrapes} (previous scrapes) | "
                f"Failed: {failed_to_process}"
            )
        
        # Log progress every 10% or at least every 20 articles
        progress_interval = max(1, min(total_articles // 10, 20))
        
        for future in concurrent.futures.as_completed(results):
            try:
                record = future.result()
                processed_count += 1
                
                if not record:
                    failed_to_process += 1
                    self.session.increment_failed_articles()
                    continue
                    
                # Check if article exists in the current batch
                if article_exists(record, data_handler):
                    self.logger.debug(
                        f"{record.id} : Article '{record.title[0:30]}' already exists in current batch: {record.id} @ {outletBrand}")
                    duplicates_in_current_batch += 1
                    self.session.increment_duplicates_current_batch()
                    self.session.increment_failed_articles()
                    continue
                
                # Check if article is in supported language before doing any more work
                if record.language not in self.languages:
                    self.logger.debug(f"Skipping article in unsupported language: {record.language}")
                    self.session.increment_failed_articles()
                    continue
                    
                # Then check if article exists in any previous scrape file
                if check_article_exists_in_all_scrapes(record, outletBrand):
                    self.logger.debug(
                        f"{record.id} : Article '{record.title[0:30]}' already exists in previous scrapes: {record.id} @ {outletBrand}")
                    duplicates_in_previous_scrapes += 1
                    self.session.increment_duplicates_previous_scrapes()
                    self.session.increment_failed_articles()
                    continue
                    
                # Article is new and in supported language, add it to processed articles
                self.processed_articles.append(record)
                self.session.increment_successful_articles()
                self.logger.debug(f"{record.id} : Article '{record.title[0:30]}'.. inserted in : {outletBrand}")
            except Exception as e:
                processed_count += 1
                failed_to_process += 1
                self.session.increment_failed_articles()
                self.logger.error(f"Error {e} scraping article from: {outletBrand}")
            
            # Log progress at regular intervals
            if processed_count % progress_interval == 0 or processed_count == total_articles:
                log_progress()

        # Final summary
        self.logger.info(
            f"Completed processing {total_articles} articles from {outletBrand}: "
            f"New: {len(self.processed_articles)} | "
            f"Duplicates: {duplicates_in_current_batch + duplicates_in_previous_scrapes} | "
            f"Failed: {failed_to_process}"
        )

        if self.processed_articles:
            self.logger.info(f"Saving {len(self.processed_articles)} new articles from {outletBrand} to database")
            data_handler.insert_multiple(self.processed_articles)
            
            # Update session info with completed time and status
            self.session.complete_session()
            
            # Return the file path and session info for further processing
            # (upload to S3 and send message to RabbitMQ will be handled by the calling service)
            return file_path