import json
from datetime import datetime
from typing import List, Set, Optional

from pydantic.main import BaseModel
from pydantic.networks import HttpUrl


class Link(BaseModel):
    url: HttpUrl
    description: Optional[str] = None


class InvolvedEntity(BaseModel):
    type: str  # "PERSON", "ORG", "LOC", etc.
    name: str
    role: Optional[str] = None  # Role or relationship to the event, e.g., "witness", "sponsor"
    links: List[Link] = []
    occurrences: int  # Number of occurrences within the event's context


class Occurrence(BaseModel):
    document_id: str
    excerpt: Optional[str] = None
    location: Optional[str] = None


class Event(BaseModel):
    date: datetime
    year: int  # Explicitly set for year-only detectors, or derived from the date
    day: int # Explicitly set for
    month: int # Explicitly set for month
    description: str
    article_id:str
    location: Optional[str] = None  # General location description
    involved_entities: List[InvolvedEntity]  # All entities (persons, orgs, locations) involved
    occurrences: List[Occurrence]
    linked_events: Set[str] = set()  # IDs of other related detectors

    @property
    def year_from_date(self) -> int:
        """Automatically derive the year from the date."""
        return self.date.year


# Convert pydantic model to dict and then to json string with custom encoder for datetime objects
class EventCustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, set):
            return list(obj)  # Convert sets to lists for JSON serialization
        return super().default(obj)
