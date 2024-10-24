# property_search.py

from typing import List, Dict, Union, Optional
from dataclasses import dataclass
import logging

logging.basicConfig(filename='property_search.log', level=logging.INFO)


@dataclass
class PropertySearchResult:
    property_key: int
    property_name: str
    total_unit_count: int
    latest_post_date: str


class PropertySearch:
    def __init__(self, cache_data: List[Dict]):
        self.properties = cache_data

    def search_properties(self,
                          search_term: Optional[str] = None,
                          property_keys: Optional[List[int]] = None) -> List[PropertySearchResult]:
        """
        Search properties by name or property keys.
        """
        results = []

        for prop in self.properties:
            # Filter by property keys if provided
            if property_keys and prop['PropertyKey'] not in property_keys:
                continue

            # Filter by search term if provided
            if search_term and search_term.lower() not in prop['PropertyName'].lower():
                continue

            results.append(PropertySearchResult(
                property_key=prop['PropertyKey'],
                property_name=prop['PropertyName'],
                total_unit_count=prop['TotalUnitCount'],
                latest_post_date=prop['LatestPostDate']
            ))

        return results