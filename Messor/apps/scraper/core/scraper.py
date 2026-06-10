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
import gc
import json
import logging
import os
import re
import time
import yaml
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional, List, Dict, Any

import newspaper
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

# Imports from the original files - kept for compatibility
from inkbytes.common.system.logger.advanced_logger import LogDestination, AdvancedLogger
from inkbytes.common.system.config.config_loader import ConfigLoader
from inkbytes.common.system.module_handler import get_module_name
from inkbytes.models.articles import Article, ArticleBuilder, ArticleCollection
from inkbytes.models.newspaperbase import NewsPaper
from inkbytes.models.outlets import OutletsSource

# v1: TinyDB was retired (INK-5). Per-cycle staging now uses a plain JSON store.
from core.staging_store import StagingStore, article_id_exists_in_file, get_staged_content_hash, load_known_article_urls

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


def _load_url_skip_patterns() -> dict:
    """Load per-outlet URL skip patterns from data/outlets/url_skip_patterns.yaml.

    Returns a dict mapping outlet slug → list[str] of substring patterns.
    Missing file is silently ignored (returns empty dict).
    """
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'outlets', 'url_skip_patterns.yaml')
    path = os.path.normpath(path)
    try:
        with open(path) as fh:
            data = yaml.safe_load(fh) or {}
        return {k: list(v) for k, v in data.items() if isinstance(v, list)}
    except FileNotFoundError:
        return {}
    except Exception as e:
        logger.warning(f"Could not load url_skip_patterns.yaml: {e}")
        return {}


# Loaded once at module import; zero overhead per-article.
_URL_SKIP_PATTERNS: dict = _load_url_skip_patterns()


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
    """Scrape articles from a given outlet — sequential article processing (ADR-0011).

    The ``num_workers`` parameter is kept for API compatibility but is no longer used.
    Articles are now processed one-at-a-time within this (outlet-level) thread so that
    at most ONE article's HTML is in memory at any moment, eliminating the OOM that the
    nested ThreadPoolExecutor caused (6.27 GB RSS → killed by cgroup).

    Outlet-level parallelism is still provided by ScraperService's outer pool
    (max_threads outlets run concurrently).
    """
    if languages is None:
        languages = ['en']
    logger.info(f"Scraping articles from: {outlet.name}")
    session = ScrapingSession()
    try:
        newsPaper = NewsPaper(agent=agent, headers=headers)
    except Exception as e:
        logger.error(f"Failed to initialize NewsPaper for: {outlet.name} with error: {e}")
        return session

    try:
        newsScraper = NewsScraper(outlet, newsPaper, session=session, languages=languages)
        newsScraper.scrape_news_outlet(outlet)
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


MAX_ARTICLES_PER_OUTLET = 300   # per-outlet download bound on the homepage-order head (ADR-0015)


def _slice_outlet_articles(articles: list) -> list:
    """Return the subset of articles to process for one outlet.

    newspaper3k discovers URLs from the homepage **and** every category page,
    so large outlets (CNN, AP, …) can surface 2,000+ links per build().

    Strategy (Messor ADR-0015): take the **homepage-order head only**, capped at
    ``MAX_ARTICLES_PER_OUTLET``.  We previously also took the last 300 ("tail")
    to capture category-page depth — but that tail is exactly where newspaper3k
    surfaces deep archive links (articles back to 2012 on theguardian), which is
    the wrong content for a fresh-news reader.  The 48-hour ``publish_date`` gate
    in ``process_outlet_articles`` is the precise freshness filter; this cap is
    now just a per-outlet **download bound** on the freshest-first head.
    """
    total = len(articles)
    head = articles[:MAX_ARTICLES_PER_OUTLET]
    if total > len(head):
        logger.info(
            f"Head slice: {total} total → {len(head)} selected "
            f"(homepage-order head, tail dropped — ADR-0015)"
        )
    return head


def process_found_articles(executor, outlet, paper) -> list:
    """
    Process articles found in a newspaper.

    Uses head+tail slicing: for large outlets newspaper3k discovers URLs from
    every category page (2,000+ links on CNN/AP). We take the first 300
    (freshest headlines) and the last 300 (deep category articles) so both
    breaking news and section coverage are represented.

    Args:
        executor: The executor to submit tasks to.
        outlet: The outlet being scraped.
        paper: The newspaper object containing articles.

    Returns:
        list: A list of futures for article scraping tasks.
    """
    articles = _slice_outlet_articles(paper.articles)
    if articles:
        total = len(paper.articles)
        capped = len(articles)
        if total > capped:
            logger.info(f"{outlet.name}: capped at {capped}/{total} articles")
        return [executor.submit(scrape_outlet_article, article, outlet.name) for article in articles]
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


_FUTURE_SKEW_DAYS = 2   # publish_date beyond now+2d is a newspaper3k body-date artefact


def is_article_fresh(record: Article, window_hours: int) -> bool:
    """Return True iff ``record.publish_date`` falls within the freshness window.

    The harvest freshness rule (Messor ADR-0015): we only bring articles
    published within the last ``window_hours`` (48h in production).  newspaper3k
    populates ``publish_date`` reliably (~99% of harvested articles), so this is
    an exact filter, not a heuristic.

    **Strict** policy (decided 2026-06-09): a missing / unparseable date returns
    ``False`` (the article is dropped).  A date absurdly in the future
    (> now + ``_FUTURE_SKEW_DAYS``) is also dropped — newspaper3k sometimes lifts
    a date from the article *body* rather than its byline, which would otherwise
    sneak a stale piece past the window.

    Comparison is done in naive-UTC; tz-aware dates are converted first.  A few
    hours of tz imprecision is irrelevant against a 48-hour window.
    """
    raw = getattr(record, "publish_date", None)
    if raw is None or str(raw).strip().lower() in ("", "none", "null"):
        return False
    try:
        from dateutil import parser as _date_parser
        dt = _date_parser.parse(str(raw))
    except (ValueError, OverflowError, TypeError):
        return False
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    now = datetime.utcnow()
    if dt > now + timedelta(days=_FUTURE_SKEW_DAYS):
        return False
    return dt >= now - timedelta(hours=window_hours)


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
            
        # Find all scrape files for this outlet, sorted NEWEST FIRST.
        # Critical: we must compare against the most recent staging file, not
        # an arbitrary one. Comparing against an old file where the article had
        # a different hash would incorrectly trigger re-publication for articles
        # that haven't changed since the last scrape.
        outlet_scrape_files = sorted(
            [
                os.path.join(scrapes_dir, f)
                for f in os.listdir(scrapes_dir)
                if outlet_name in f and f.endswith(".db.json")
            ],
            key=os.path.getmtime,
            reverse=True,          # newest first — stop at first match
        )

        if not outlet_scrape_files:
            logger.debug(f"No existing scrape files found for outlet: {outlet_name}")
            return False

        logger.debug(f"Checking {len(outlet_scrape_files)} scrape files (newest-first) for outlet: {outlet_name}")

        # ── PERF-REVIEW ────────────────────────────────────────────────────────
        # Content-aware cross-session dedup (2026-06-06, checkpoint/content-aware-dedup).
        # Iterate newest-first and stop at the FIRST file that contains this
        # article ID — that file holds the most recent known version.
        # Fast revert if this becomes a bottleneck:
        #   git revert 6cbef06   # restores pure-ID dedup
        # ── END PERF-REVIEW ────────────────────────────────────────────────────
        import hashlib as _hashlib
        article_id    = article.id
        article_title = article.title[:30] if article.title else "Unknown"
        new_hash = _hashlib.md5(
            ((article.title or "") + (article.text or "")).encode("utf-8")
        ).hexdigest()

        for file_path in outlet_scrape_files:
            try:
                stored_hash = get_staged_content_hash(file_path, article_id)
                if stored_hash is None:
                    continue  # article not in this file — check older files

                # Found the most recent prior record for this article.
                if stored_hash == new_hash:
                    logger.info(
                        f"Article '{article_title}' (ID: {article_id}) unchanged in "
                        f"{os.path.basename(file_path)} — skipping"
                    )
                    return True  # genuine duplicate

                # Content changed since last scrape — re-publish.
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
        #
        # Drop the meta_lang guard: langdetect is used downstream in
        # ArticleBuilder.buildFromNewspaper3K, so a missing/wrong meta_lang
        # no longer causes valid articles (especially from Spanish outlets) to
        # be silently discarded here.
        if article.is_parsed and article.text:
            return article
    except ValueError as e:
        handle_error_in_article_processing(article, e)
    except Exception as e:
        # Catch network errors (Timeout, ConnectionError, TooManyRedirects, …)
        # that newspaper3k raises beyond ValueError so they are logged and
        # counted as failures rather than crashing the thread.
        logging.getLogger().warning(f"Download/parse failed for {getattr(article, 'url', '?')}: {type(e).__name__}: {e}")


def scrape_outlet_article(article: newspaper.Article, newsPaperBrand: str) -> Article:
    """Scrape a single article — download, parse, extract, then free HTML (ADR-0011 L2).

    Called sequentially (no executor) so only one article's HTML is in memory at a
    time per outlet thread.  After ``create_article_record()`` extracts what we need,
    the newspaper.Article's HTML + lxml parse tree are explicitly nullified so the
    garbage collector can reclaim them without waiting for a cyclic-GC pass.
    """
    try:
        newspaperArticle = build_newspaper_article(article)
        if newspaperArticle and len(newspaperArticle.text) > 150:
            record = create_article_record(newspaperArticle, newsPaperBrand)
            # Layer 2: free the HTML + lxml tree immediately after extraction.
            # newspaper.Article holds article.html (1–3 MB) and clean_doc (lxml
            # etree with ~50 k circular-ref nodes).  Nullifying them here lets
            # CPython's refcount GC reclaim them before the next article starts.
            newspaperArticle.html = None
            newspaperArticle.clean_doc = None
            newspaperArticle.clean_top_node = None
            return record
    except Exception as e:
        logging.getLogger().warning(
            f"scrape_outlet_article failed for {getattr(article, 'url', '?')}: {type(e).__name__}: {e}"
        )
    finally:
        # Belt-and-suspenders: clear regardless of success/failure path.
        try:
            article.html = None
            article.clean_doc = None
            article.clean_top_node = None
        except Exception:
            pass


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

    def __init__(self, outlet: OutletsSource, paper: NewsPaper, executor: object = None,
                 session: ScrapingSession = None, languages=None):
        """Initialise a NewsScraper.

        ``executor`` is kept for API compatibility but is no longer used — article
        processing is sequential (ADR-0011).  Pass ``None`` or omit it.
        """
        if languages is None:
            languages = ['en']
        self.newspaper = paper
        self.processed_articles = ArticleCollection()
        self.outlet = outlet
        self.executor = executor          # retained for compat; unused internally
        self.logger = logging.getLogger(self.__class__.__name__)
        self.stats = ScrapingStats()
        self.session = session or ScrapingSession()
        self.languages = languages

    def scrape_news_outlet(self, executor_or_outlet=None, outlet=None) -> ScrapingSession:
        """Scrape articles from a news outlet — sequential, no inner thread pool (ADR-0011).

        Signature accepts the old two-arg form ``(executor, outlet)`` and the new
        single-arg form ``(outlet)`` so callers don't need to be updated atomically.
        """
        # Accept both (executor, outlet) and (outlet,) call signatures.
        if outlet is None:
            outlet = executor_or_outlet   # new single-arg call
        # else: two-arg old call — executor_or_outlet is the unused executor

        try:
            self.session.outlet_name = outlet.name
            if not validate_outlet_url(outlet):
                self.logger.info(f"Invalid outlet URL {outlet.url}")
                return self.session

            # Build the newspaper (fetches homepage + categories).
            paper = self.newspaper.build(outlet)

            # Slice the article list BEFORE freeing the paper object.
            # Head+tail strategy: first 300 (breaking) + last 300 (category depth).
            np_articles = _slice_outlet_articles(paper.articles)
            self.session.total_articles = len(np_articles)

            # Layer 2 / ADR-0011: free the paper's category-page HTML immediately —
            # we only need the article URL list from here on.
            try:
                paper.categories = []
                paper.category_urls = []
            except Exception:
                pass
            del paper

            if not np_articles:
                self.logger.info(f"No articles found from {outlet.name}")
                return self.session

            # Layer 3 / ADR-0011: load known article URLs once before the loop.
            scrapes_dir = config.storage.staging.local.scraping()
            known_urls: set = load_known_article_urls(scrapes_dir, outlet.name)
            self.logger.info(
                f"Saving {len(np_articles)} articles for {outlet.name} "
                f"({len(known_urls)} previously seen URLs)"
            )

            self.process_outlet_articles(outlet.name, np_articles, known_urls)

        except Exception as e:
            self.logger.error(f"Error scraping {outlet}: {e}")
        finally:
            self.session.complete_session()
        return self.session

    def process_outlet_articles(self, outletBrand: str, np_articles: list,
                               known_urls: set) -> None:
        """Sequential article processing — ADR-0011 Layers 1, 2, 3.

        Replaces the futures-based loop with a plain for-loop so only ONE article's
        HTML is in memory at a time.  URL pre-dedup (Layer 3) skips known articles
        without any HTTP request.  Explicit HTML cleanup + periodic gc.collect()
        (Layer 2) prevent lxml garbage accumulation.

        Args:
            outletBrand:  Outlet name used for staging file naming and logging.
            np_articles:  List of ``newspaper.Article`` objects (URL populated,
                          not yet downloaded).
            known_urls:   Set of article URLs already seen in prior staging files
                          (loaded once before this call — ADR-0011 Layer 3).
        """
        # Per-RUN staging file (Messor ADR-0014).  Previously this used
        # generate_today_timestamp() (midnight UTC), so ONE file per outlet
        # accumulated every cycle's new articles across the whole day.
        # _publish_articles_from_staging_file() re-reads the WHOLE file each
        # cycle, so a per-day file re-published earlier cycles' articles on every
        # run (≈4×/day amplification) — and after the ADR-0016 migration wiped the
        # dedup volume, the per-day files ballooned to multi-MB and were
        # re-published in full each cycle (the 105 143-message flood, 2026-06-09).
        # A per-RUN timestamp gives each cycle its own file containing ONLY that
        # run's new articles, so re-publishing it == publishing only-new.
        # Cross-run / cross-day dedup is unchanged: load_known_article_urls()
        # still scans every staging file in the 7-day window (ADR-0012).
        run_ts = int(time.time())
        self.session.set_results_staging_file_name(f"{run_ts}.{outletBrand}.db.json")
        staging_path = config.storage.staging.local.scraping()
        file_path = os.path.join(staging_path, self.session.results_staging_file_name)
        self.logger.info(f"Saving articles to: {file_path}")
        data_handler = StagingStore(file_path)

        # Harvest freshness window (Messor ADR-0015): only articles published in
        # the last N hours are staged.  Configurable via `articles.freshness_
        # window_hours`; defaults to 48h if unset.
        window_hours = int(config.articles.freshness_window_hours() or 48)

        total           = len(np_articles)
        url_skipped     = 0   # Layer 3 pre-dedup hits (no download)
        batch_dupes     = 0   # within this cycle's staging file
        lang_skipped    = 0
        stale_skipped   = 0   # published outside the freshness window (or undated)
        parse_failed    = 0
        progress_every  = max(1, min(total // 10, 20))

        self.logger.info(f"Processing {total} articles from {outletBrand}")

        for i, np_article in enumerate(np_articles):

            # ── Layer 3: URL pre-dedup — skip without downloading ────────────
            article_url = getattr(np_article, 'url', None)
            if article_url and article_url in known_urls:
                url_skipped += 1
                self.session.increment_duplicates_previous_scrapes()
                self.session.increment_failed_articles()
                continue

            # ── Layer 3b: per-outlet URL blocklist (data/outlets/url_skip_patterns.yaml)
            # Skips non-news sections (e.g. BBC Maestro, Travel, Future) before
            # any HTTP request is made. Patterns are substring matches on the URL.
            skip_patterns = _URL_SKIP_PATTERNS.get(outletBrand, [])
            if article_url and skip_patterns:
                if any(pat in article_url for pat in skip_patterns):
                    url_skipped += 1
                    self.session.increment_failed_articles()
                    continue

            # ── Layer 1: sequential download + scrape ────────────────────────
            try:
                record = scrape_outlet_article(np_article, outletBrand)
                # scrape_outlet_article() nullifies html/clean_doc (Layer 2)
            except Exception as e:
                parse_failed += 1
                self.session.increment_failed_articles()
                self.logger.warning(
                    f"Article {article_url} failed: {type(e).__name__}: {e}"
                )
                continue

            if not record:
                parse_failed += 1
                self.session.increment_failed_articles()
                continue

            # Current-batch dedup (same cycle, same outlet)
            if article_exists(record, data_handler):
                batch_dupes += 1
                self.session.increment_duplicates_current_batch()
                self.session.increment_failed_articles()
                continue

            # Language filter
            if record.language not in self.languages:
                lang_skipped += 1
                self.session.increment_failed_articles()
                continue

            # Freshness gate (ADR-0015): only articles published within the last
            # `window_hours` are staged.  Strict — a missing/unparseable date is
            # treated as stale and dropped.  This is what stops month-old archive
            # links (theguardian back to 2012) from being re-published as "fresh".
            if not is_article_fresh(record, window_hours):
                stale_skipped += 1
                self.session.increment_failed_articles()
                continue

            # New article — accept
            self.processed_articles.append(record)
            self.session.increment_successful_articles()
            if article_url:
                known_urls.add(article_url)   # prevent re-processing if URL repeats

            # ── Layer 2: periodic forced GC to collect lxml circular refs ────
            if i > 0 and i % 20 == 0:
                gc.collect()

            if (i + 1) % progress_every == 0 or (i + 1) == total:
                self.logger.info(
                    f"Progress: {i+1}/{total} ({(i+1)/total*100:.1f}%) | "
                    f"New: {len(self.processed_articles)} | "
                    f"URL-skip: {url_skipped} | batch-dupe: {batch_dupes} | "
                    f"stale-skip: {stale_skipped} | "
                    f"parse-fail: {parse_failed} | lang-skip: {lang_skipped}"
                )

        # ── Final summary + flush ─────────────────────────────────────────────
        total_dupes = url_skipped + batch_dupes
        self.logger.info(
            f"Completed {outletBrand}: new={len(self.processed_articles)} "
            f"url-skip={url_skipped} batch-dupe={batch_dupes} "
            f"stale-skip={stale_skipped} (>{window_hours}h or undated) "
            f"parse-fail={parse_failed} lang-skip={lang_skipped}"
        )

        if self.processed_articles:
            data_handler.insert_multiple(self.processed_articles)
            return file_path