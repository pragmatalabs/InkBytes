# --------------------------------
# OutletsSource Class
# --------------------------------
import json
import logging
from enum import Enum

from pydantic import BaseModel, Field

__name__ = "Data Source Model"
logger = logging.getLogger(__name__)


class OutletsDataSource(Enum):
    REST_API = "rest_api"
    JSON_FILE = "json_file"


class Attributes(BaseModel):
    name: str
    url: str
    active: bool
    description: str = Field(default="")
    slug: str = Field(default="")
    logo: str = Field(default="")


class OutletsSource(BaseModel):
    # Default attributes that can be overridden during initialization
    id: int = None
    documentId: str = None
    name: str = ""
    url: str = ""
    active: bool = True
    description: str = None
    slug: str = None
    createdAt: str = None
    updatedAt: str = None
    publishedAt: str = None
    # RSS/Atom feed URL — None means no feed configured; scraper uses newspaper3k fallback.
    feed_url: str = None

    # For compatibility with existing code that expects attributes field
    attributes: Attributes = None
    
    def __init__(self, **data):
        # Handle both direct fields and nested attributes structure
        if 'attributes' in data:
            super().__init__(**data)
        else:
            # Create attributes field from the provided data
            attributes_data = {
                'name': data.get('name', ''),
                'url': data.get('url', ''),
                'active': data.get('active', True),
                'description': data.get('description', ''),
                'slug': data.get('slug', '')
            }
            super().__init__(attributes=Attributes(**attributes_data), **data)
    
    def to_json(self) -> str:
        return json.dumps(self.model_dump())
    
    def get_attributes(self):
        return self.attributes


class OutletsHandler(BaseModel):
    news_outlets: list[OutletsSource] = []

    def add_outlets_from_payload(self, payload):
        try:
            if isinstance(payload, dict) and 'data' in payload:
                # Extract the data list from the payload
                items = payload.get('data', [])
                for outlet in items:
                    # Replace None values with empty strings for string fields
                    for key in ['description', 'slug']:
                        if key in outlet and outlet[key] is None:
                            outlet[key] = ''
                    outlet_source = OutletsSource(**outlet)
                    self.add(outlet_source)
            else:
                # Original behavior for backward compatibility
                for outlet in payload:
                    # Replace None values with empty strings for string fields
                    if isinstance(outlet, dict):
                        for key in ['description', 'slug']:
                            if key in outlet and outlet[key] is None:
                                outlet[key] = ''
                    outlet_source = OutletsSource(**outlet)
                    self.add(outlet_source)
        except Exception as e:
            import logging
            logging.getLogger().error(f"Error in add_outlets_from_payload: {e}")
            raise

    def add(self, outlet: OutletsSource):
        self.news_outlets.append(outlet)

    def remove_outlet(self, key: str):
        self.news_outlets.pop(key, None)

    def remove_outlet_by_name(self, name: str):
        self.news_outlets = [outlet for outlet in self.news_outlets if outlet['name'] != name]

    def get_outlet_url(self, name: str):
        return self.news_outlets.get(name)

    def get_all_outlets(self):
        return self.news_outlets

    def to_json(self) -> str:
        return json.dumps(self.dict())

    @classmethod
    def from_json(cls, json_str: str) -> "OutletsCollection":
        data = json.loads(json_str)
        return cls(**data)
