# --------------------------------
# Article Class
# --------------------------------
import json
import re
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

import langdetect
import newspaper
from pydantic import BaseModel, Field

__name__ = "Article Class"

from .entities import Entity, EntitiesCollection

import logging

logger = logging.getLogger(__name__)


class Article(BaseModel):
    id: Optional[str] = Field(default=None, primary_key=True)
    uid: Optional[str] = None
    doc_id: Optional[int] = None
    publish_date: Optional[str] = None
    category: Optional[str] = None
    meta_categories: Optional[List[str]] = []
    fetched_on: Optional[str] = None
    last_updated: Optional[str] = None
    cluster: Optional[str | int] = None
    factual: Optional[str] = None
    sentiment: Optional[str] = None
    entities: Optional[EntitiesCollection | list | dict | Dict] = []
    article_url: Optional[str] = None
    article_source: Optional[str] = None
    title: Optional[str] = None
    text: Optional[str] = None
    authors: Optional[List[str]] = None
    summary: Optional[str] = None
    similars: Optional[List[str] | list | dict | Dict] = []
    related: Optional[List[str] | list | dict | Dict] = []
    topics: Optional[List[str]] = []
    source_url: Optional[str] = None
    language: Optional[str] = "en"
    keywords: Optional[List[str]] = []
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")
    cluster_centroid: Optional[int] = None

    class Config:
        arbitrary_types_allowed = True
        from_attributes = True

    def __getitem__(self, key):
        return self.__dict__

    def from_dict(self, data: Dict):
        return self(**data)

    def to_dict(self):
        article_dict = self.__dict__.copy()
        '''article_dict["entities"] = [
            entity.to_dict() for entity in self.entities
        ]  # Convert EntitiesCollection to list of dictionaries
        return article_dict'''
        article_dict["entities"] = [entity.to_dict()
                                    if hasattr(entity, 'to_dict')
                                    else entity for entity in
                                    self.entities]
        return article_dict

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def to_json(self) -> str:
        return json.dumps(self, cls=ArticleEncoder)

    def set_topics(self, topics):
        self.topics = topics

    def update(self, article):
        _article = article.to_dict()
        for key, value in _article.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise KeyError(f"Invalid field '{key}' for Article")

    def encode(self):
        return json.dumps(self.__dict__)

    # def __str__(self):
    #    return f"{self.title} {self.id}"

    def get_entities(self):
        return self.entities

    def get_topics(self):
        return self.topics

    def set_entities(self, entitiesCollection: EntitiesCollection):
        self.entities = [entity for entity in entitiesCollection]
        return self.entities

    def get_entity_links(self, entity_type):
        links = []
        for entity in self.entities:
            if entity["type"] == entity_type:
                links.extend(entity["links"])
        return links

    def get_all_entity_types(self):
        entity_types = set()
        for entity in self.entities:
            entity_types.add(entity["type"])
        return list(entity_types)

    def get_links(self):
        return self.links

    def set_links(self, links):
        self.links = links

    def get_entities_by_type(self, entity_type):
        entities = []
        for entity in self.entities:
            if entity["type"] == entity_type:
                entities.append(entity)
        return entities

    def add_related_article(self, article):
        self.related.append(article)

    def get_related_articles(self):
        return self.related

    def add_similars_article(self, article):
        self.similars.append(article)

    def get_similars_articles(self):
        return self.similars

    def add_topic(self, topic):
        self.topics.append(topic)

    def get_category(self):
        return self.category

    def get_word_count(self):
        return len(self.text.split())

    def get_top_keywords(self, num_keywords=3):
        return sorted(self.keywords, key=lambda x: x[1], reverse=True)[:num_keywords]

    def set_sentiment(self, sentiment):
        self.sentiment = sentiment

    def set_factual(self, factual):
        self.factual = factual

    def set_summary(self, summary):
        self.summary = summary

    def extract_category(self):
        # Extracting category from the URL
        self.category = self.article_url.split("/")[-2]
        return self.category
    def extract_main_category(self, metadata: dict) -> str:
        """
        Extract the most probable main category from article metadata and URL.
        
        This function uses a prioritized approach to determine the main category,
        checking various metadata fields in order of reliability.
        
        Args:
            metadata: The complete metadata dictionary
            
        Returns:
            str: The most probable main category
        """
        # List of possible category sources in order of priority
        possible_sources = []
        
        # 1. Check for explicitly marked primary category in metadata
        primary_fields = [
            ('article', 'primarySection'),
            ('article', 'primaryCategory'),
            ('metadata', 'primarySection'),
            ('schema', 'articleSection'),
            ('og', 'section'),
            ('twitter', 'section'),
            ('page', 'sectionName'),
            ('article', 'section')
        ]
        
        for section, field in primary_fields:
            section_data = metadata.get(section, {})
            if isinstance(section_data, dict) and field in section_data:
                value = section_data[field]
                if value and isinstance(value, str):
                    possible_sources.append(value)
        
        # 2. Check for category arrays and take the first one
        category_arrays = [
            'categories',
            'sections',
            'primaryTaxonomy'
        ]
        
        for array_name in category_arrays:
            if array_name in metadata and isinstance(metadata[array_name], list) and metadata[array_name]:
                first_item = metadata[array_name][0]
                if isinstance(first_item, str) and first_item:
                    possible_sources.append(first_item)
                elif isinstance(first_item, dict) and ('name' in first_item or 'term' in first_item):
                    value = first_item.get('name', first_item.get('term', ''))
                    if value and isinstance(value, str):
                        possible_sources.append(value)
        
        # 3. Extract from the URL path
        url_parts = self.article_url.split('/')
        url_parts = [part for part in url_parts if part]  # Remove empty parts
        
        # Check if we have enough parts in the URL
        if len(url_parts) >= 3:
            # Common news URL structures often have the section as the first path component after the domain
            # Example: example.com/politics/2023/article-name
            domain_index = 0
            for i, part in enumerate(url_parts):
                if '.' in part:  # This is likely the domain
                    domain_index = i
                    break
            
            if domain_index + 1 < len(url_parts):
                section_from_url = url_parts[domain_index + 1]
                # Filter out common non-category URL segments
                non_categories = ['news', 'articles', 'story', 'content', 'post']
                date_pattern = re.compile(r'^\d{4}$|^\d{2}$|^\d{4}-\d{2}$|^\d{4}-\d{2}-\d{2}$')
                
                if (section_from_url not in non_categories and 
                    not date_pattern.match(section_from_url) and
                    not section_from_url.startswith('index')):
                    possible_sources.append(section_from_url)
            
            # Also try the second-to-last URL part as in your original approach
            if len(url_parts) >= 2:
                possible_sources.append(url_parts[-2])
        
        # 4. Check for generic categories that might be lists
        general_fields = [
            ('article', 'category'),
            ('metadata', 'category'),
            ('og', 'category'),
            ('twitter', 'category')
        ]
        
        for section, field in general_fields:
            section_data = metadata.get(section, {})
            if isinstance(section_data, dict) and field in section_data:
                value = section_data[field]
                if value:
                    if isinstance(value, str):
                        categories = [cat.strip() for cat in value.split(',')]
                        if categories:
                            possible_sources.append(categories[0])
                    elif isinstance(value, list) and value:
                        possible_sources.append(value[0])
        
        # 5. Check for tags (lower priority than sections/categories)
        tag_fields = [
            ('article', 'tag'),
            ('metadata', 'tag'),
            ('article', 'primaryTag')
        ]
        
        for section, field in tag_fields:
            section_data = metadata.get(section, {})
            if isinstance(section_data, dict) and field in section_data:
                value = section_data[field]
                if value:
                    if isinstance(value, str):
                        tags = [tag.strip() for tag in value.split(',')]
                        if tags:
                            possible_sources.append(tags[0])
                    elif isinstance(value, list) and value:
                        possible_sources.append(value[0])
        
        # 6. Fallback options if all else fails
        fallbacks = ['article', 'news', 'general']
        
        # Return the first valid category found, or a fallback
        for source in possible_sources:
            # Clean up the category
            category = source.strip()
            
            # Basic normalization
            category = category.lower()
            
            # Remove any common prefixes or suffixes
            category = re.sub(r'^(category-|section-|topic-)', '', category)
            
            # Skip empty or very short categories
            if category and len(category) > 1:
                return category
        
        # If no valid category was found, return the first fallback
        return fallbacks[0]
    
    def extract_main_category_from_list(self, meta_categories):
        """
        Extract the most probable main category from an existing list of categories.
        
        Args:
            meta_categories: List of categories already extracted
                
        Returns:
            str: The most probable main category
        """
        # If there are no categories, return a default
        if not meta_categories or len(meta_categories) == 0:
            return self.article_url.split("/")[-2] or "article"
        
        # Convert all categories to lowercase for comparison
        lowercase_categories = [cat.lower() for cat in meta_categories]
        
        # Deprioritize these generic terms
        generic_terms = ["article", "story", "content", "post", "latest"]
        
        # Priority categories - these are often main sections in news sites
        priority_categories = [
            "news", "world", "politics", "business", "technology", "science", 
            "religion", "opinion", "culture", "arts",
            "health", "sports", "entertainment", "opinion", "culture", "arts", 
            "breaking news", "us news", "europe", "asia", "africa", "americas",
            "middle east", "economy", "markets", "finance", "money",
            "lifestyle", "travel", "food", "education", "environment", "world news"
        ]
        
        # Countries and regions (for international news)
        countries_regions = [
            "ukraine", "russia", "china", "india", "japan", "usa", "u.s.", "united states",
            "uk", "united kingdom", "france", "germany", "israel", "palestine",
            "middle east", "europe", "asia", "africa", "americas", "australia"
        ]
        
        # Filter out generic categories if we have better options
        filtered_categories = []
        filtered_lowercase = []
        
        for i, cat in enumerate(meta_categories):
            if not any(generic.lower() == lowercase_categories[i] for generic in generic_terms):
                filtered_categories.append(cat)
                filtered_lowercase.append(lowercase_categories[i])
        
        # If filtering removed everything, use original lists
        if not filtered_categories:
            filtered_categories = meta_categories
            filtered_lowercase = lowercase_categories
        
        # First, look for exact matches with priority categories
        for i, cat_lower in enumerate(filtered_lowercase):
            if cat_lower in priority_categories:
                return filtered_categories[i]
        
        # Second, look for categories that contain priority words
        for i, cat_lower in enumerate(filtered_lowercase):
            for priority in priority_categories:
                if priority in cat_lower:
                    return filtered_categories[i]
        
        # Third, check for country/region names for international news
        for i, cat_lower in enumerate(filtered_lowercase):
            for location in countries_regions:
                if location in cat_lower:
                    return filtered_categories[i]
        
        # Fourth, check for title case categories that often indicate main sections
        # (like "World & Nation")
        title_case_categories = [cat for cat in filtered_categories if ' ' in cat and 
                                not cat.islower() and not cat.isupper()]
        if title_case_categories:
            return title_case_categories[0]
        
        # If we still don't have a match, choose a reasonable length category
        reasonable_length_cats = [cat for cat in filtered_categories if 3 <= len(cat) <= 25]
        if reasonable_length_cats:
            # Prefer shorter categories as they're often main sections
            reasonable_length_cats.sort(key=len)
            return reasonable_length_cats[0]
        
        # If all else fails, take the first non-generic category
        if filtered_categories:
            return filtered_categories[0]
        
        # Last resort: original URL-based fallback
        return self.article_url.split("/")[-2] or "article"
class ArticleBuilder(BaseModel):
    id: str = None
    uid: str = None
    publish_date: str = None
    fetched_on: str = None
    last_updated: str = None
    last_update: str = None
    cluster: str = None
    factual: str = None
    sentiment: str = None
    entities: EntitiesCollection = EntitiesCollection()
    article_url: str = None
    article_source: str = None
    title: str = None
    text: str = None
    authors: str = None
    summary: str = None
    similars: List[Dict] = []
    meta_categories: List[Dict] =[]
    related: List[Dict] = []
    topics: List[str] = []
    source_url: str = None
    language: str = "en"
    keywords: List[str] = []
    metadata: List[str] = []
    version: str = None
    social_media: List[str] = []
    pure_text: str = None
    signature: str = None

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True

    def buildFromNewspaper3K(
            self, article: newspaper.Article, newsPaperBrand: str
    ) -> Article:
        articleData = {}
        try:
            articleData = {
                "fetched_on": str(datetime.now()),
                "id": str(uuid.uuid3(uuid.NAMESPACE_URL, article.url)),
                "uid": str(uuid.uuid3(uuid.NAMESPACE_URL, article.url)),
                "title": article.title or "untitled",
                "text": article.text,
                "authors": article.authors or [],
                "publish_date": str(article.publish_date),
                "source_url": newsPaperBrand,
                "article_url": article.url,
                "keywords": article.keywords,
                "summary": article.summary,
                "similars": [],
                "entities": [],
                "related": [],
                "topics": [],
                "sentiment": "",
                "factual": "",
                "language": langdetect.detect(article.text) or "en",
                "last_updated": str(datetime.now()),
                "metadata": article.meta_data or None,
                "category": article.meta_data.get("category") or None,
                "meta_categories": []
            }
        except ValueError as e:
            logger.error(f"Error fetching article: {e}")
        return Article(**articleData)


class ArticleEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Article):
            return obj.to_dict()
        if isinstance(obj, Entity):
            return obj.to_dict()
        if isinstance(obj, EntitiesCollection):
            return (
                obj.to_list()
            )  # Serialize EntitiesCollection as a list of dictionaries
        return super().default(obj)


class ArticleCollection(BaseModel):
    articles: List[Article] = []

    def __iter__(self):
        return iter(self.articles)

    def __len__(self):
        return len(self.articles)

    def count(self):
        return len(self.articles)

    def append(self, article):
        self.add_article(article)

    def add_article(self, article):
        self.articles.append(article)

    def size(self):
        return len(self.articles)

    def remove_article(self, article):
        self.articles.remove(article)

    def filter_articles(self, filter_func):
        filtered_articles = [
            article for article in self.articles if filter_func(article)
        ]
        filtered_collection = ArticleCollection()
        filtered_collection.articles = filtered_articles
        return filtered_collection

    def find_article(self, article_id):
        for article in self.articles:
            if article.id == article_id:
                return article
        return None

    def save_to_json(self, file_path):
        data = [article.to_dict() for article in self.articles]
        with open(file_path, "w") as file:
            json.dump(data, file)

    def load_from_json(self, file_path):
        with open(file_path, "r") as file:
            data = json.load(file)
            for article_data in data:
                article = Article.from_dict(article_data)
                self.add_article(article)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.articles[key.start: key.stop: key.step]
        else:
            return self.articles[key]

    def __setitem__(self, key, value):
        self.articles[key] = value

    def add_article(self, article):
        # Add an article to the collection
        self.articles.append(article)

    def get_article(self, id):
        # get the article in the collection that has the given id
        for article in self.articles:
            if article.id == id:
                return article

    def remove_article(self, article):
        # Remove an article from the collection
        self.articles.remove(article)

    def save_to_json(self, file_path):
        # Save the collection to a JSON file
        data = [article.to_json() for article in self.articles]
        with open(file_path, "w") as file:
            json.dump(data, file)

    def load_articles_from_json(self, data):
        builder = ArticleBuilder()
        self.articles = [
            builder.from_json(article_data).build() for article_data in data
        ]

    def load_from_json(self, file_path):
        # Load the collection from a JSON file
        with open(file_path, "r") as file:
            data = json.load(file)
            for article_data in data:
                article = Article(article_data)
                self.add_article(article)

    def to_dict(self):
        # Convert the collection to a Python dictionary
        return {"articles": [article.to_dict() for article in self.articles]}

    def from_dict(self, data):
        # Create an ArticleCollection object from a Python dictionary
        collection = self()
        if "articles" in data:
            for article_data in data["articles"]:
                article = Article(article_data)
                self.add_article(article)
        return collection

    def filter_articles(self, filter_func):
        # Filter the articles in the collection using a filter function
        filtered_articles = [
            article for article in self.articles if filter_func(article)
        ]
        # Create a new ArticleCollection object with the filtered articles
        filtered_collection = ArticleCollection()
        filtered_collection.articles = filtered_articles
        return filtered_collection


def build_article_collection(documents) -> ArticleCollection:
    _articles: ArticleCollection = ArticleCollection()
    for article_data in documents:
        article = Article(vars(article_data))
        article.doc_id = article_data.doc_id
        _articles.append(article)
    return _articles


def group_articles_by_cluster(articles) -> dict:
    clusters = {}
    for article in articles:
        cluster_id = article.cluster
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(article)
    return clusters


def extract_unique_clusters(articles: ArticleCollection) -> List[int]:
    cluster_numbers = set()
    for article in articles:
        cluster_numbers.add(article.cluster)
    unique_clusters = list(cluster_numbers)
    return unique_clusters


class ArticleProcessor:
    pass
