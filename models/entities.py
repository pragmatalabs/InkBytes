"""
Entity Model and Deduplication Module

This module provides entity representation classes and intelligent entity deduplication
functionality for handling similar entity mentions in texts.

Typical use cases:
- Representing extracted named entities (people, organizations, locations, etc.)
- Deduplicating similar entity mentions (e.g., "Donald Trump" vs "Trump, Donald")
- Tracking entity occurrence counts across variations
- Selecting canonical entity forms for consistent representation

Author: Julian Delarosa (juliandelarosa@icloud.com)
Copyright (c) 2023-2025 InkBytes. All rights reserved.
Version: 1.0
"""

import json
import logging
from typing import List, Dict, Optional

from pydantic import BaseModel, Field

__name__ = "Entity Model Class"
__author__ = "Julian Delarosa"
__copyright__ = "Copyright 2023-2025, InkBytes"
__license__ = "MIT"
__version__ = "1.0"
__maintainer__ = "Julian Delarosa"
__email__ = "juliandelarosa@icloud.com"
__status__ = "Production"

logger = logging.getLogger(__name__)


class Entity(BaseModel):
    """Entity representation for named entities extracted from text documents.
    
    This class represents extracted named entities (people, organizations, locations, etc.),
    storing entity type, name, associated links, and occurrence counts.
    
    Attributes:
        type: The entity type (e.g., 'PERSON', 'ORG', 'GPE', 'LOC')
        name: The textual name of the entity
        links: References to external knowledge resources (e.g., Wikipedia URLs)
        ocurrences: Count of how many times this entity appears in the text
                   (or the aggregated count after deduplication)
    """
    type: Optional[str]
    name: Optional[str]
    links: Optional[List[str]]
    ocurrences: Optional[int]

    def to_dict(self) -> Dict:
        """Convert entity to dictionary representation."""
        return {
            "type": self.type or "",
            "name": self.name or "",
            "links": self.links or [],
            "ocurrences": self.ocurrences or 1
        }

    @classmethod
    def from_dict(cls, data: any):
        """Create entity from dictionary representation."""
        for entity_info in data:
            entity = Entity(**entity_info)
        return entity

    @classmethod
    def from_json(cls, json_data: str):
        """Create entity from JSON string."""
        data = json.loads(json_data)
        return cls.from_dict(data)

    def to_json(self) -> str:
        """Convert entity to JSON string."""
        data = self.to_dict()
        if len(data) > 0:
            return json.dumps(data, cls=EntityEncoder)
        else:
            return "{}"

    def __hash__(self):
        """Generate hash for entity (for set operations)."""
        return hash((self.type, self.name, tuple(self.links or [])))

    def __repr__(self):
        """Return string representation of entity."""
        return f"Entity(type={self.type}, name={self.name}, links={self.links}, ocurrences={self.ocurrences})"

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
        from_attributes = True


class EntityEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Entity):
            return obj.to_dict()
        return super().default(obj)


def normalize_entity_name(entity_name: str) -> str:
    """Normalize entity names for consistent comparison across variations.
    
    This function standardizes entity names by handling different formats, 
    punctuation, and capitalization to facilitate more accurate entity matching.
    
    Examples:
        >>> normalize_entity_name("Donald J. Trump")
        "donald j trump"
        >>> normalize_entity_name("Trump, Donald")
        "trump donald"
    
    Args:
        entity_name: The original entity name to normalize
    
    Returns:
        str: Normalized entity name for comparison
    """
    if not entity_name:
        return ""
    
    # Convert to lowercase for case-insensitive comparison
    name = entity_name.lower()
    
    # Remove punctuation that doesn't affect meaning
    for char in [',', '.', ';', ':', '"', "'", '`', '-']:
        name = name.replace(char, ' ')
        
    # Normalize whitespace
    name = ' '.join(name.split())
    
    return name


def are_similar_entities(name1: str, name2: str) -> bool:
    """Determine if two entity names are similar or variations of each other.
    
    This function uses multiple heuristics to detect when two differently formatted
    entity mentions likely refer to the same underlying entity. It handles common
    variations such as:
    
    1. Full name vs. last name only ("Donald Trump" vs "Trump")
    2. Different formats ("Trump, Donald" vs "Donald Trump")
    3. Middle initial/name variations ("Donald J. Trump" vs "Donald Trump")
    4. Significant word overlap
    
    Examples:
        >>> are_similar_entities("Donald Trump", "Trump, Donald")
        True
        >>> are_similar_entities("Donald J. Trump", "Trump")
        True
        >>> are_similar_entities("Joe Biden", "Donald Trump")
        False
    
    Args:
        name1: First entity name to compare
        name2: Second entity name to compare
    
    Returns:
        bool: True if entities are likely variations of each other, False otherwise
    """
    # If names are identical, they're similar
    if name1 == name2:
        return True
        
    # Normalize both names
    norm1 = normalize_entity_name(name1)
    norm2 = normalize_entity_name(name2)
    
    # If normalized names are identical, they're similar
    if norm1 == norm2:
        return True
        
    # Handle cases like "Donald Trump" vs "Trump" or "Trump, Donald"
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    
    # If one name is a subset of the other (e.g., "Trump" is in "Donald Trump")
    if words1.issubset(words2) or words2.issubset(words1):
        return True
        
    # Check if there's significant overlap between words
    common_words = words1.intersection(words2)
    # If they share at least 2 significant words or 50% of words in the shorter name
    min_len = min(len(words1), len(words2))
    if len(common_words) >= 2 or (min_len > 0 and len(common_words) / min_len >= 0.5):
        return True
    
    # Special case for names: Check if last names match (often the most important identifier)
    # This handles "Donald Trump" vs "Donald J. Trump"
    if len(words1) > 1 and len(words2) > 1:
        last_word1 = norm1.split()[-1]
        last_word2 = norm2.split()[-1]
        if last_word1 == last_word2 and len(last_word1) > 3:  # Only meaningful last names
            # Check if first letters of first names match too
            first_letter1 = norm1.split()[0][0] if norm1.split()[0] else ''
            first_letter2 = norm2.split()[0][0] if norm2.split()[0] else ''
            if first_letter1 == first_letter2:
                return True
    
    return False


def find_best_entity_name(names: List[str]) -> str:
    """Select the most complete entity name from a list of similar variations.
    
    When multiple name variations exist for the same entity, this function
    selects the "best" or most canonical form based on completeness heuristics.
    
    The scoring algorithm prioritizes:
    1. Names with more words (weighted higher)
    2. Longer names (as they tend to be more complete)
    
    Examples:
        >>> find_best_entity_name(["Trump", "Donald Trump", "Donald J. Trump"])
        "Donald J. Trump"
        >>> find_best_entity_name(["Biden", "Joe Biden"])
        "Joe Biden"
    
    Args:
        names: List of similar entity name variations
    
    Returns:
        str: The best canonical entity name form, or empty string if input is empty
    """
    if not names:
        return ""
        
    # Prefer longer names as they're usually more complete
    # But also consider names with more words, as they might be more specific
    scored_names = []
    for name in names:
        word_count = len(name.split())
        length = len(name)
        # Score based on word count (higher weight) and length
        score = (word_count * 10) + length
        scored_names.append((name, score))
    
    # Return the name with the highest score
    return max(scored_names, key=lambda x: x[1])[0]


def create_unique_entities(data_source: List[Entity]) -> List[Entity]:
    """Deduplicate and merge similar entity mentions into canonical representations.
    
    This is the main entity deduplication function that processes a list of entities 
    and returns a deduplicated list with merged similar entities. The function uses
    a two-pass algorithm:
    
    1. First pass: Group entities by exact type and name, combining duplicates
    2. Second pass: For specific entity types (people, organizations, locations),
       cluster similar entity mentions and merge them with intelligent name selection
    
    The function handles cases like "Donald Trump", "Trump", and "Donald J. Trump" being
    recognized as the same entity, with occurrence counts aggregated appropriately.
    
    Examples:
        Merging entity mentions with similar names:
        
        Input entities:
        - Entity(type='PERSON', name='Donald Trump', ocurrences=1)
        - Entity(type='PERSON', name='Trump', ocurrences=1)
        - Entity(type='PERSON', name='Donald J. Trump', ocurrences=1)
        
        Output:
        - Entity(type='PERSON', name='Donald J. Trump', ocurrences=3)
    
    Args:
        data_source: List of Entity objects potentially containing duplicates
                    and similar entity mentions
    
    Returns:
        List[Entity]: Deduplicated entities with merged counts and best name forms,
                     sorted by occurrence count (most frequent first)
    """
    # First pass - group by exact type and name
    exact_entities_dict = {}
    
    # Group by entity type for second pass
    type_grouped_entities = {}
    
    # First pass - handle exact matches
    for entity in data_source:
        entity_type_label = entity.type
        entity_name_text = entity.name
        entity_url_links = entity.links if entity.links else []

        # Use a tuple of type and name as the key for uniqueness
        key = (entity_type_label, entity_name_text)

        # Check if the entity already exists with exact match
        if key in exact_entities_dict:
            # Increment occurrences
            exact_entities_dict[key].ocurrences = (exact_entities_dict[key].ocurrences or 1) + 1
            # Update links if necessary, avoiding duplicates
            if entity_url_links:
                existing_links = exact_entities_dict[key].links or []
                exact_entities_dict[key].links = list(set(existing_links + entity_url_links))
        else:
            # Clone the entity to avoid mutating the original objects in data_source
            cloned_entity = Entity(
                type=entity_type_label, 
                name=entity_name_text,
                links=entity_url_links, 
                ocurrences=1
            )
            exact_entities_dict[key] = cloned_entity
            
            # Group by type for second pass
            if entity_type_label not in type_grouped_entities:
                type_grouped_entities[entity_type_label] = []
            type_grouped_entities[entity_type_label].append(cloned_entity)

    # Second pass - for each type, merge similar entities
    for entity_type, entities in type_grouped_entities.items():
        # Skip small entity lists or non-name entity types
        if len(entities) <= 1 or entity_type not in ['PERSON', 'ORG', 'GPE', 'LOC', 'NORP']:
            continue
            
        # Build clusters of similar entities
        processed_entities = set()
        clusters = []
        
        for i, entity in enumerate(entities):
            if entity in processed_entities:
                continue
                
            # Start a new cluster with this entity
            cluster = [entity]
            processed_entities.add(entity)
            
            # Find similar entities
            for other_entity in entities[i+1:]:
                if other_entity in processed_entities:
                    continue
                    
                if are_similar_entities(entity.name, other_entity.name):
                    cluster.append(other_entity)
                    processed_entities.add(other_entity)
            
            clusters.append(cluster)
        
        # Merge each cluster
        for cluster in clusters:
            if len(cluster) <= 1:
                continue
                
            # Find the primary entity (keep the first one as reference)
            primary_entity = cluster[0]
            
            # Find the best name from all entities in the cluster
            entity_names = [e.name for e in cluster]
            best_name = find_best_entity_name(entity_names)
            
            # Update the primary entity with the best name
            primary_entity.name = best_name
            
            # Merge occurrences and links from other entities in the cluster
            for other_entity in cluster[1:]:
                primary_entity.ocurrences = (primary_entity.ocurrences or 1) + (other_entity.ocurrences or 1)
                if other_entity.links:
                    primary_entity.links = list(set((primary_entity.links or []) + other_entity.links))
                
                # Remove the other entity from our exact_entities_dict
                if (other_entity.type, other_entity.name) in exact_entities_dict:
                    del exact_entities_dict[(other_entity.type, other_entity.name)]

    # Extract unique entities into a list
    unique_entities = list(exact_entities_dict.values())
    
    # Sort by occurrence count (most frequent first)
    unique_entities.sort(key=lambda e: (e.ocurrences or 1), reverse=True)

    return unique_entities



class EntitiesCollection(BaseModel):
    """
    Author: Julian Delarosa (juliandelarosa@icloud.com)
    Date: 2023-07-14
    Version: 1.0
    Description:
        A class used to represent a collection of Entity objects. It extends the List class from the typing module.

    System: URIHarvest v1.0
    Language: Python 3.10
    License: GNU General Public License (GPL)

    Notes:
        - This class provides methods for adding an entity to the collection, getting entities by type,
        converting the collection to a list, removing duplicate entities, and converting the collection to a JSON string.

    Attributes
    ----------
    entities : List[Entity]
        a list of Entity objects
    """

    entities: List[Entity] = Field(default_factory=list)

    def add_entity(self, entity: Entity) -> None:
        """
        Adds an entity to the collection if it's not already in the collection.

        Parameters:
            entity (Entity): The entity to add.

        Returns:
            None
        """
        if entity not in self.entities:
            self.entities.append(entity)

    def get_entities_by_type(self, entity_type: str) -> List[Entity]:
        """
        Returns a list of entities that match the given type.

        Parameters:
            entity_type (str): The type of entities to retrieve.

        Returns:
            List[Entity]: List of entities with the specified type.
        """
        return [entity for entity in self.entities if entity.type == entity_type]

    def to_list(self) -> List[Entity]:
        """
        Returns a list representation of the collection.

        Returns:
            List[Entity]: A list of entities.
        """
        return self.entities

    def remove_duplicates(self) -> None:
        """
        Removes duplicate entities from the collection.
        """
        seen = set()
        unique_entities = []  # Corrected initialization
        for entity in self.entities:
            # Create a hashable representation of the entity for comparison
            entity_tuple = tuple(
                (k, v if not isinstance(v, dict) else tuple(v.items()))
                for k, v in entity.to_dict().items()
            )
            if entity_tuple not in seen:
                seen.add(entity_tuple)
                unique_entities.append(entity)
        self.entities = unique_entities

    def __iter__(self):
        return iter(self.entities)

    def __len__(self):
        return len(self.entities)

    @classmethod
    def from_list(cls, entities_data: List[Dict]) -> "EntitiesCollection":
        """
        Creates an EntityCollection from a list of dictionaries.

        Parameters:
            entities_data (List[Dict]): List of dictionaries representing entities.

        Returns:
            EntitiesCollection: An instance of the EntityCollection.
        """
        entity_collection = cls(entities=[])
        for entity_data in entities_data:
            entity = Entity(**entity_data)
            entity_collection.add_entity(entity)
        return entity_collection

    def to_json(self) -> str:
        """
        Returns a JSON string representation of the collection.

        Returns:
            str: JSON string representation of the collection.
        """
        return json.dumps(self.entities, indent=4, cls=EntityEncoder)

    def to_string(self) -> str:
        """
        Returns a string representation of the collection.

        Returns:
            str: String representation of the collection.
        """
        return "\n".join(str(entity) for entity in self.entities)

    @classmethod
    def from_json(cls, json_data: str) -> "EntitiesCollection":
        """
        Creates an EntityCollection from a JSON string.

        Parameters:
            json_data (str): JSON string representation of the collection.

        Returns:
            EntitiesCollection: An instance of the EntityCollection.
        """
        entities_data = json.loads(json_data)
        return cls.from_list(entities_data)

    class Config:
        arbitrary_types_allowed = True
        from_attributes: True
