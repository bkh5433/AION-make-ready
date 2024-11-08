from typing import List, Optional, Dict, Union
from datetime import datetime, date
from logger_config import LogConfig
from models.models import (Property,
                           WorkOrderMetrics,
                           PropertyStatus,
                           PropertySearchResult,
                           BaseResponse)

# Setup logging
log_config = LogConfig()
logger = log_config.get_logger('property_search')

class PropertySearch:
    def __init__(self, cache_data: List[Dict]):
        logger.info(f"Initializing PropertySearch with {len(cache_data) if cache_data else 0} records")
        self.properties = self._convert_to_models(cache_data)

    def _parse_date(self, date_value: Union[str, datetime, date]) -> datetime:
        """
        Parse different date formats into datetime object.

        Args:
            date_value: Can be string, datetime, or date object

        Returns:
            datetime object
        """
        if date_value is None:
            return None

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
        """Convert raw cache data to Property models with computed metrics"""
        logger.info("Starting data conversion to models")
        properties = []

        if not cache_data:
            logger.warning("No cache data provided")
            return properties

        for index, data in enumerate(cache_data):
            try:
                logger.debug(f"\n{'=' * 80}\nProcessing property {index + 1}/{len(cache_data)}")
                logger.debug(f"Raw data: {data}")

                # Parse dates first
                period_start = data.get('PeriodStartDate')
                period_end = data.get('PeriodEndDate')

                logger.debug(f"Raw dates - start: {period_start}, end: {period_end}")

                if period_start:
                    period_start = self._parse_date(period_start)
                if period_end:
                    period_end = self._parse_date(period_end)

                logger.debug(f"Parsed dates - start: {period_start}, end: {period_end}")

                # Map SQL column names to model fields
                metrics_data = {
                    'open_work_orders': int(data.get('OpenWorkOrder_Current', 0)),
                    'new_work_orders': int(data.get('NewWorkOrders_Current', 0)),
                    'completed_work_orders': int(data.get('CompletedWorkOrder_Current', 0)),
                    'cancelled_work_orders': int(data.get('CancelledWorkOrder_Current', 0)),
                    'pending_work_orders': int(data.get('PendingWorkOrders', 0)),
                    'percentage_completed': float(data.get('PercentageCompletedThisPeriod', 0)),
                    'average_days_to_complete': float(data.get('AverageDaysToComplete', 0)),
                    'period_start_date': period_start,
                    'period_end_date': period_end,
                    'days_per_month': 21
                }

                logger.debug(f"Metrics data prepared: {metrics_data}")

                # Create metrics object
                logger.debug("Creating WorkOrderMetrics object...")
                metrics = WorkOrderMetrics(**metrics_data)
                logger.debug(f"WorkOrderMetrics created successfully: {metrics.model_dump()}")

                # Parse latest post date

                # Create property object
                logger.debug("Creating Property object...")
                property = Property(
                    property_key=int(data['PropertyKey']),
                    property_name=str(data['PropertyName']),
                    total_unit_count=int(data['TotalUnitCount']),
                    # latest_post_date=latest_post_date,
                    status=PropertyStatus.ACTIVE,
                    metrics=metrics
                )
                logger.debug(f"Property created successfully: {property.model_dump()}")

                properties.append(property)
                logger.debug(f"Successfully processed property {data['PropertyName']}")
                logger.debug(f"{'=' * 80}\n")

            except Exception as e:
                logger.error(f"Error converting property {index} data: {str(e)}", exc_info=True)
                logger.error(f"Problematic data: {data}")
                # Print full exception traceback for debugging
                import traceback
                logger.error(f"Full traceback:\n{traceback.format_exc()}")
                continue

        logger.info(f"Completed conversion - {len(properties)} properties processed")

        # Log sample of converted data
        if properties:
            logger.debug("Sample of converted property:")
            logger.debug(f"First property: {properties[0].model_dump()}")
        else:
            logger.warning("No properties were successfully converted")

        return properties

    def search_properties(self,
                          search_term: Optional[str] = None,
                          property_keys: Optional[List[int]] = None,
                          include_analytics: bool = False) -> List[Property]:
        """Search properties by name or property keys."""
        logger.info(f"Searching properties - term: {search_term}, keys: {property_keys}")
        results = []

        for property in self.properties:
            if property_keys and property.property_key not in property_keys:
                continue

            if search_term and search_term.lower() not in property.property_name.lower():
                continue

            if include_analytics and property.metrics:
                property.metrics = self._enhance_metrics(property.metrics)

            results.append(property)

        logger.info(f"Search complete - found {len(results)} properties")
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
        logger.info("Getting search results")

        properties = self.search_properties(
            search_term=search_term,
            property_keys=property_keys,
            include_analytics=True
        )

        if period_info:
            logger.debug(f"Updating period info: {period_info}")
            for prop in properties:
                if prop.metrics:
                    prop.metrics.period_start_date = period_info.get('start_date')
                    prop.metrics.period_end_date = period_info.get('end_date')

        result = PropertySearchResult(
            count=len(properties),
            data=properties,
            last_updated=last_updated or datetime.now(),
            period_info=period_info
        )

        logger.info("Search result created")
        return result
