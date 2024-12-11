from typing import List, Optional, Dict, Union
from datetime import datetime, date, timezone
from pydantic import ValidationError
from logger_config import LogConfig
from models.Property import Property, PropertyStatus
from models.WorkOrderMetrics import WorkOrderMetrics
from models.WorkOrderAnalytics import WorkOrderAnalytics
from models.PropertySearchResult import PropertySearchResult
import time


# Setup logging
log_config = LogConfig()
logger = log_config.get_logger('property_search')


class PropertySearch:
    def __init__(self, cache_data: List[Dict]):
        start_time = time.perf_counter()
        # Index raw data by PropertyKey and create name index for search
        self._raw_cache = {item['PropertyKey']: item for item in cache_data}
        self._name_index = {item['PropertyKey']: item['PropertyName'].lower() for item in cache_data}
        self.data_issues = []

        end_time = time.perf_counter()
        logger.info(f"PropertySearch initialized with {len(cache_data)} properties in {(end_time - start_time):.3f}s")

    def _convert_property(self, property_data: Dict) -> Optional[Property]:
        """Convert a single property's raw data to a Property model"""
        try:
            # Map data to metrics model
            metrics_data = {
                'open_work_orders': property_data.get('OpenWorkOrder_Current', 0),
                'actual_open_work_orders': property_data.get('ActualOpenWorkOrders_Current', 0),
                'new_work_orders': property_data.get('NewWorkOrders_Current', 0),
                'completed_work_orders': property_data.get('CompletedWorkOrder_Current', 0),
                'cancelled_work_orders': property_data.get('CancelledWorkOrder_Current', 0),
                'pending_work_orders': property_data.get('PendingWorkOrders', 0),
                'percentage_completed': property_data.get('PercentageCompletedThisPeriod', 0.0),
                'average_days_to_complete': property_data.get('AverageDaysToComplete', 0.0),
                'days_per_month': 21,
            }

            metrics = WorkOrderMetrics(**metrics_data)

            # Parse dates
            latest_post_date = self._parse_date(property_data.get('LatestPostDate'))
            period_start = self._parse_date(property_data.get('PeriodStartDate'))
            period_end = self._parse_date(property_data.get('PeriodEndDate'))

            return Property(
                property_key=property_data['PropertyKey'],
                property_name=property_data['PropertyName'],
                total_unit_count=property_data['TotalUnitCount'],
                latest_post_date=latest_post_date,
                status=PropertyStatus.ACTIVE,
                metrics=metrics,
                period_start_date=period_start,
                period_end_date=period_end
            )

        except ValidationError as e:
            self._handle_error(property_data, 'validation_error', str(e))
        except Exception as e:
            self._handle_error(property_data, 'processing_error', str(e))
        return None

    def search_properties(self,
                          search_term: Optional[str] = None,
                          property_keys: Optional[List[int]] = None,
                          include_analytics: bool = False) -> List[Property]:
        """Search properties by name or property keys with optional analytics"""
        start_time = time.perf_counter()

        matching_keys = []

        # If searching by specific keys, use those directly
        if property_keys:
            matching_keys = [key for key in property_keys if key in self._raw_cache]
            logger.info(f"Key-based search found {len(matching_keys)} of {len(property_keys)} requested keys")
        else:
            # If we have a search term, use the name index
            search_term_lower = search_term.lower() if search_term else None
            if search_term_lower:
                matching_keys = [
                    key for key, name in self._name_index.items()
                    if search_term_lower in name
                ]
                logger.info(f"Text search '{search_term}' found {len(matching_keys)} matches")
            else:
                # For empty searches, return all keys
                matching_keys = list(self._raw_cache.keys())
                logger.info(f"Empty search returning all {len(matching_keys)} properties")

        # Convert matching properties
        results = []
        conversion_start = time.perf_counter()
        conversion_errors = 0

        for key in matching_keys:
            property_data = self._raw_cache[key]
            property = self._convert_property(property_data)
            if property:
                if include_analytics and property.metrics:
                    try:
                        analytics = WorkOrderAnalytics(
                            daily_rate=property.metrics.daily_rate,
                            monthly_rate=property.metrics.monthly_rate,
                            break_even_target=property.metrics.break_even_target,
                            current_output=property.metrics.current_output,
                            average_days_to_complete=property.metrics.average_days_to_complete,
                            completion_percentage=property.metrics.percentage_completed
                        )
                        property.analytics = analytics
                    except Exception as e:
                        logger.error(f"Analytics error for property {property.property_key}: {str(e)}")
                        conversion_errors += 1
                results.append(property)
            else:
                conversion_errors += 1

        end_time = time.perf_counter()

        # Log final performance metrics
        conversion_time = end_time - conversion_start
        total_time = end_time - start_time
        success_rate = (len(results) / len(matching_keys)) * 100 if matching_keys else 0

        logger.info(
            f"Search completed in {total_time:.3f}s (conversion: {conversion_time:.3f}s) - "
            f"Converted: {len(results)}/{len(matching_keys)} ({success_rate:.1f}%) - "
            f"Errors: {conversion_errors}"
        )
        
        return results

    def _handle_error(self, data: Dict, error_type: str, message: str) -> None:
        """Handle and log errors during property conversion"""
        error_detail = {
            'property_key': data.get('PropertyKey', 'Unknown'),
            'property_name': data.get('PropertyName', 'Unknown'),
            'error_type': error_type,
            'message': message
        }
        self.data_issues.append(error_detail)
        logger.error(f"{error_type} for property {error_detail['property_name']}: {message}")

    def _parse_date(self, date_value: Union[str, datetime, date]) -> datetime:
        """Parse date values into datetime objects"""
        if date_value is None:
            return None
            
        try:
            if isinstance(date_value, datetime):
                return date_value
            elif isinstance(date_value, date):
                return datetime.combine(date_value, datetime.min.time())
            elif isinstance(date_value, str):
                try:
                    return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        return datetime.strptime(date_value, '%Y-%m-%d')
                    except ValueError:
                        pass
            raise ValueError(f"Unable to parse date value: {date_value}")
        except Exception as e:
            logger.error(f"Date parsing error: {str(e)}")
            raise

    def get_search_result(self,
                          search_term: Optional[str] = None,
                          property_keys: Optional[List[int]] = None,
                          last_updated: Optional[datetime] = None,
                          period_info: Optional[Dict[str, datetime]] = None) -> PropertySearchResult:
        """Get formatted search result with metadata"""
        properties = self.search_properties(search_term, property_keys)

        result = PropertySearchResult(
            count=len(properties),
            data=properties,
            last_updated=last_updated or datetime.now(),
            period_info=period_info,
            data_issues=self.data_issues if self.data_issues else None
        )

        return result
