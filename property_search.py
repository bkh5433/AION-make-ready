from typing import List, Optional, Dict, Union
from datetime import datetime, date, timezone
from pydantic import ValidationError
from logger_config import LogConfig
from models.Property import Property, PropertyStatus
from models.WorkOrderMetrics import WorkOrderMetrics
from models.WorkOrderAnalytics import WorkOrderAnalytics
from models.PropertySearchResult import PropertySearchResult


# Setup logging
log_config = LogConfig()
logger = log_config.get_logger('property_search')


class PropertySearch:
    def __init__(self, cache_data: List[Dict]):
        self.properties = []
        self.data_issues = []  # Track problematic data
        self._convert_to_models(cache_data)
        logger.info(f"Initialized PropertySearch with {len(self.properties)} properties")

    def _parse_date(self, date_value: Union[str, datetime, date]) -> datetime:
        """
        Parse different date formats into UTC datetime object.

        Args:
            date_value: Can be string, datetime, or date object

        Returns:
            datetime object in UTC
        """
        if date_value is None:
            return None

        if isinstance(date_value, datetime):
            # Ensure datetime is UTC
            return date_value.astimezone(timezone.utc)
        elif isinstance(date_value, date):
            # Convert date to UTC datetime
            return datetime.combine(date_value, datetime.min.time(), tzinfo=timezone.utc)
        elif isinstance(date_value, str):
            try:
                # Parse GMT format (already UTC)
                return datetime.strptime(date_value, '%a, %d %b %Y %H:%M:%S GMT').replace(tzinfo=timezone.utc)
            except ValueError:
                try:
                    # Parse ISO format and convert to UTC
                    dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                    return dt.astimezone(timezone.utc)
                except ValueError:
                    # Parse date-only format as UTC
                    return datetime.strptime(date_value, '%Y-%m-%d').replace(tzinfo=timezone.utc)

        raise ValueError(f"Unable to parse date value: {date_value}")

    def _convert_to_models(self, cache_data: List[Dict]) -> None:
        """Convert raw cache data to Property models with comprehensive error handling"""
        success_count = 0

        for data in cache_data:
            try:
                logger.debug(f"Converting property data: {data}")

                # Map data to metrics model
                metrics_data = {
                    'open_work_orders': data.get('OpenWorkOrder_Current', 0),
                    'actual_open_work_orders': data.get('ActualOpenWorkOrders_Current', 0),
                    'new_work_orders': data.get('NewWorkOrders_Current', 0),
                    'completed_work_orders': data.get('CompletedWorkOrder_Current', 0),
                    'cancelled_work_orders': data.get('CancelledWorkOrder_Current', 0),
                    'pending_work_orders': data.get('PendingWorkOrders', 0),
                    'percentage_completed': data.get('PercentageCompletedThisPeriod', 0.0),
                    'average_days_to_complete': data.get('AverageDaysToComplete', 0.0),
                    'days_per_month': 21,  # Default value
                }

                # Create metrics instance with validation
                metrics = WorkOrderMetrics(**metrics_data)

                # Parse dates
                latest_post_date = self._parse_date(data.get('LatestPostDate'))
                period_start = self._parse_date(data.get('PeriodStartDate'))
                period_end = self._parse_date(data.get('PeriodEndDate'))

                # Create property instance
                property = Property(
                    property_key=data['PropertyKey'],
                    property_name=data['PropertyName'],
                    total_unit_count=data['TotalUnitCount'],
                    latest_post_date=latest_post_date,
                    status=PropertyStatus.ACTIVE,
                    metrics=metrics,
                    period_start_date=period_start,
                    period_end_date=period_end
                )

                self.properties.append(property)
                success_count += 1

            except ValidationError as e:
                error_detail = {
                    'property_key': data.get('PropertyKey', 'Unknown'),
                    'property_name': data.get('PropertyName', 'Unknown'),
                    'error_type': 'validation_error',
                    'message': str(e)
                }
                self.data_issues.append(error_detail)
                logger.error(f"Validation error for property {error_detail['property_name']}: {str(e)}")
                continue
            except Exception as e:
                error_detail = {
                    'property_key': data.get('PropertyKey', 'Unknown'),
                    'property_name': data.get('PropertyName', 'Unknown'),
                    'error_type': 'processing_error',
                    'message': str(e)
                }
                self.data_issues.append(error_detail)
                logger.error(f"Processing error for property {error_detail['property_name']}: {str(e)}")
                continue

        logger.info(f"Completed conversion - {success_count} properties processed")

        if not self.properties:
            logger.warning("No properties were successfully converted")

    def search_properties(self,
                          search_term: Optional[str] = None,
                          property_keys: Optional[List[int]] = None,
                          include_analytics: bool = False) -> List[Property]:
        """Search properties by name or property keys with optional analytics"""
        results = []

        for property in self.properties:
            # Filter by property keys if provided
            if property_keys and property.property_key not in property_keys:
                continue

            # Filter by search term if provided
            if search_term and search_term.lower() not in property.property_name.lower():
                continue

            # Include additional analytics if requested
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
                    logger.error(f"Error calculating analytics for property {property.property_key}: {str(e)}")

            results.append(property)

        return results

    def _enhance_metrics(self, metrics: WorkOrderMetrics) -> WorkOrderMetrics:
        """Add additional analytics calculations to metrics"""
        try:
            # Calculate efficiency score
            total_orders = (metrics.open_work_orders + metrics.new_work_orders +
                            metrics.completed_work_orders + metrics.cancelled_work_orders)

            if total_orders > 0:
                efficiency_score = round(
                    (metrics.completed_work_orders / total_orders) * 100, 1
                )
                setattr(metrics, 'efficiency_score', efficiency_score)

            # Calculate backlog rate
            if metrics.completed_work_orders > 0:
                backlog_rate = round(
                    (metrics.open_work_orders + metrics.pending_work_orders) /
                    metrics.completed_work_orders, 2
                )
                setattr(metrics, 'backlog_rate', backlog_rate)

        except Exception as e:
            logger.error(f"Error enhancing metrics: {str(e)}")

        return metrics

    def get_search_result(self,
                          search_term: Optional[str] = None,
                          property_keys: Optional[List[int]] = None,
                          last_updated: Optional[datetime] = None,
                          period_info: Optional[Dict[str, datetime]] = None) -> PropertySearchResult:
        """Get formatted search result with metadata"""
        properties = self.search_properties(search_term, property_keys)
        return PropertySearchResult(
            count=len(properties),
            data=properties,
            last_updated=last_updated or datetime.now(),
            period_info=period_info,
            data_issues=self.data_issues if self.data_issues else None  # Include data issues in response
        )
