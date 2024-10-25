from typing import List, Optional, Dict, Union
from datetime import datetime, date
import logging
from models.models import (Property,
                           WorkOrderMetrics,
                           PropertyStatus,
                           PropertySearchResult,
                           BaseResponse)


logging.basicConfig(filename='property_search.log', level=logging.INFO)

class PropertySearch:
    def __init__(self, cache_data: List[Dict]):
        self.properties = self._convert_to_models(cache_data)

    def _parse_date(self, date_value: Union[str, datetime, date]) -> datetime:
        """
        Parse different date formats into datetime object.

        Args:
            date_value: Can be string, datetime, or date object

        Returns:
            datetime object
        """
        if isinstance(date_value, datetime):
            return date_value
        elif isinstance(date_value, date):
            return datetime.combine(date_value, datetime.min.time())
        elif isinstance(date_value, str):
            try:
                # Try parsing GMT format
                return datetime.strptime(date_value, '%a, %d %b %Y %H:%M:%S GMT')
            except ValueError:
                try:
                    # Try parsing ISO format
                    return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                except ValueError:
                    # Try parsing date-only format
                    return datetime.strptime(date_value, '%Y-%m-%d')

    def _convert_to_models(self, cache_data: List[Dict]) -> List[Property]:
        """Convert raw cache data to Property models"""
        properties = []
        for data in cache_data:
            try:
                metrics = WorkOrderMetrics(
                    open_work_orders=data['OpenWorkOrder_Current'],
                    new_work_orders=data['NewWorkOrders_Current'],
                    completed_work_orders=data['CompletedWorkOrder_Current'],
                    cancelled_work_orders=data['CancelledWorkOrder_Current'],
                    pending_work_orders=data['PendingWorkOrders'],
                    percentage_completed=data['PercentageCompletedThisPeriod']
                )

                latest_post_date = self._parse_date(data['LatestPostDate'])

                property = Property(
                    property_key=data['PropertyKey'],
                    property_name=data['PropertyName'],
                    total_unit_count=data['TotalUnitCount'],
                    latest_post_date=latest_post_date,
                    status=PropertyStatus.ACTIVE,
                    metrics=metrics
                )
                properties.append(property)
            except Exception as e:
                logging.error(f"Error converting property data: {str(e)}")
                continue

        return properties

    def search_properties(self,
                          search_term: Optional[str] = None,
                          property_keys: Optional[List[int]] = None) -> List[Property]:
        """Search properties by name or property keys."""
        results = []

        for property in self.properties:
            # Filter by property keys if provided
            if property_keys and property.property_key not in property_keys:
                continue

            # Filter by search term if provided
            if search_term and search_term.lower() not in property.property_name.lower():
                continue

            results.append(property)

        return results

    def get_search_result(self,
                          search_term: Optional[str] = None,
                          property_keys: Optional[List[int]] = None,
                          last_updated: Optional[datetime] = None) -> PropertySearchResult:
        """Get formatted search result with metadata"""
        properties = self.search_properties(search_term, property_keys)
        return PropertySearchResult(
            count=len(properties),
            data=properties,
            last_updated=last_updated or datetime.now()
        )
