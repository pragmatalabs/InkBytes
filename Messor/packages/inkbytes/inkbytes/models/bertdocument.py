from typing import List, Optional, Dict

from pydantic import BaseModel

from entities import Entity


class Metadata(BaseModel):
    author: Optional[str]
    copyright: Optional[str]
    description: Optional[str]
    id: Optional[str]
    keywords: Optional[str]
    news_keywords: Optional[str]
    content_type: Optional[str]
    og: Optional[Dict]
    article: Optional[Dict]
    twitter: Optional[Dict]
    fb: Optional[Dict]


class BertDocument(BaseModel):
    uid: Optional[str]
    category: Optional[str]
    entries: Optional[List[Entity]]
    similars: Optional[List["BertDocument"]]
    related: Optional[List["BertDocument"]]
    title: Optional[str]
    summary: Optional[str]
    tags: Optional[List[str]]
    keywords: Optional[List[str]]
    metadata: Optional[Metadata]

    class Config:
        arbitrary_types_allowed = True
        from_attributes = True


BertDocument.model_rebuild()
