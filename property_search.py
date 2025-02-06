from typing import List, Optional, Dict, Union, Tuple
from datetime import datetime, date, timezone, timedelta
from pydantic import ValidationError
from logger_config import LogConfig
from models.Property import Property, PropertyStatus
from models.WorkOrderMetrics import WorkOrderMetrics
from models.WorkOrderAnalytics import WorkOrderAnalytics
from models.PropertySearchResult import PropertySearchResult
from monitoring import SystemMonitor
import time
from difflib import get_close_matches


# Setup logging
log_config = LogConfig()
logger = log_config.get_logger('property_search')

# Initialize system monitor
system_monitor = SystemMonitor()

# Cache configuration
CONVERSION_CACHE_TTL = timedelta(minutes=5)  # Cache entries expire after 5 minutes

# State name to code mapping
STATE_MAPPING = {
    'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR', 'california': 'CA',
    'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE', 'florida': 'FL', 'georgia': 'GA',
    'hawaii': 'HI', 'idaho': 'ID', 'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA',
    'kansas': 'KS', 'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
    'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS', 'missouri': 'MO',
    'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV', 'new hampshire': 'NH', 'new jersey': 'NJ',
    'new mexico': 'NM', 'new york': 'NY', 'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH',
    'oklahoma': 'OK', 'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
    'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT', 'vermont': 'VT',
    'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV', 'wisconsin': 'WI', 'wyoming': 'WY',
    'district of columbia': 'DC', 'puerto rico': 'PR',
    # # Add Canadian provinces if needed
    # 'alberta': 'AB', 'british columbia': 'BC', 'manitoba': 'MB', 'new brunswick': 'NB',
    # 'newfoundland and labrador': 'NL', 'nova scotia': 'NS', 'ontario': 'ON', 'prince edward island': 'PE',
    # 'quebec': 'QC', 'saskatchewan': 'SK'
}

# Create reverse mapping (code to name) and add codes as keys too
STATE_SEARCH_MAPPING = {**STATE_MAPPING}
STATE_SEARCH_MAPPING.update({v.lower(): v for v in STATE_MAPPING.values()})


def get_fuzzy_state_match(search_term: str, cutoff: float = 0.6) -> Optional[str]:
    """Find closest matching state name or code using fuzzy matching"""
    search_term_lower = search_term.lower().strip()

    # Try exact match first
    if search_term_lower in STATE_SEARCH_MAPPING:
        return STATE_SEARCH_MAPPING[search_term_lower]

    # Try partial matches first
    partial_matches = [(key, STATE_SEARCH_MAPPING[key]) for key in STATE_SEARCH_MAPPING.keys()
                       if search_term_lower in key]
    if partial_matches:
        return partial_matches[0][1]  # Return the state code of the first partial match

    # Try fuzzy matching against state names and codes
    matches = get_close_matches(
        search_term_lower,
        STATE_SEARCH_MAPPING.keys(),
        n=3,
        cutoff=cutoff
    )

    if matches:
        best_match = matches[0]
        logger.debug(f"Fuzzy matched state '{search_term}' to '{best_match}' (other possibilities: {matches[1:]})")
        return STATE_SEARCH_MAPPING[best_match]

    return None


def get_fuzzy_name_matches(search_term: str, names: Dict[int, str], cutoff: float = 0.6) -> set:
    """Find property keys with names that fuzzy match the search term"""
    search_term_lower = search_term.lower().strip()

    # Create reverse mapping of names to keys for easier lookup
    name_to_keys = {}
    for key, name in names.items():
        name_lower = name.lower()
        if name_lower in name_to_keys:
            name_to_keys[name_lower].add(key)
        else:
            name_to_keys[name_lower] = {key}

    # Try exact substring match first
    exact_matches = {
        key for name_lower, keys in name_to_keys.items()
        for key in keys
        if search_term_lower in name_lower
    }

    if exact_matches:
        logger.debug(f"Found exact substring matches for '{search_term}': {len(exact_matches)} properties")
        return exact_matches

    # Try fuzzy matching if no exact matches
    matches = get_close_matches(
        search_term_lower,
        name_to_keys.keys(),
        n=5,
        cutoff=cutoff
    )

    if matches:
        fuzzy_matches = set()
        for match in matches:
            fuzzy_matches.update(name_to_keys[match])
        logger.debug(f"Fuzzy matched name '{search_term}' to: {matches}")
        return fuzzy_matches

    return set()


class PropertySearch:
    # Class-level cache that persists across instances
    _global_conversion_cache = {}
    _global_cache_timestamps = {}
    _global_last_cleanup = datetime.now(timezone.utc)

    def __init__(self, cache_data: List[Dict]):
        start_time = time.perf_counter()

        if not cache_data:
            logger.error("Attempted to initialize PropertySearch with empty cache data")
            raise ValueError("Cache data cannot be None or empty")

        # Index raw data by PropertyKey and create indexes for search
        try:
            self._raw_cache = {item['PropertyKey']: item for item in cache_data}
            self._name_index = {item['PropertyKey']: item['PropertyName'].lower() for item in cache_data}
            # Create state code index with normalized state codes
            self._state_index = {
                item['PropertyKey']: item.get('PropertyStateProvinceCode', '').lower().strip()
                for item in cache_data
            }

            # Create city index with normalized city names
            self._city_index = {
                item['PropertyKey']: item.get('PropertyCity', '').lower().strip()
                for item in cache_data
            }

            # Use class-level caches
            self._conversion_cache = self._global_conversion_cache
            self._cache_timestamps = self._global_cache_timestamps
            self._last_cleanup = self._global_last_cleanup

            # Log unique states in the index for debugging
            unique_states = set(state for state in self._state_index.values() if state)
            logger.debug(f"Initialized with unique states: {unique_states}")

            self.data_issues = []

            end_time = time.perf_counter()
            logger.info(
                f"PropertySearch initialized with {len(cache_data)} properties in {(end_time - start_time) * 1000:.3f}ms")
        except (TypeError, KeyError) as e:
            logger.error(f"Error initializing PropertySearch: {str(e)}")
            logger.error(f"Cache data type: {type(cache_data)}")
            if cache_data:
                logger.error(f"First item type: {type(cache_data[0]) if len(cache_data) > 0 else 'no items'}")
            raise ValueError(f"Invalid cache data format: {str(e)}")

    def _cleanup_expired_cache_entries(self) -> None:
        """Remove expired entries from the conversion cache"""
        now = datetime.now(timezone.utc)
        expired_keys = [
            key for key, timestamp in self._cache_timestamps.items()
            if now - timestamp > CONVERSION_CACHE_TTL
        ]

        for key in expired_keys:
            self._conversion_cache.pop(key, None)
            self._cache_timestamps.pop(key, None)

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

        # Update the class-level last cleanup time
        self.__class__._global_last_cleanup = now

    def _convert_property(self, property_data: Dict) -> Optional[Property]:
        """Convert a single property's raw data to a Property model"""
        property_key = property_data['PropertyKey']
        now = datetime.now(timezone.utc)

        # Cleanup expired entries periodically (every minute)
        if now - self._last_cleanup > timedelta(minutes=1):
            self._cleanup_expired_cache_entries()

        # Check if property is already in conversion cache and not expired
        if property_key in self._conversion_cache and property_key in self._cache_timestamps:
            cache_timestamp = self._cache_timestamps[property_key]
            if now - cache_timestamp <= CONVERSION_CACHE_TTL:
                logger.debug(
                    f"Cache hit for property {property_key} (age: {(now - cache_timestamp).total_seconds():.1f}s)")
                return self._conversion_cache[property_key]
            else:
                # Remove expired entry
                logger.debug(
                    f"Cache entry expired for property {property_key} (age: {(now - cache_timestamp).total_seconds():.1f}s)")
                self._conversion_cache.pop(property_key, None)
                self._cache_timestamps.pop(property_key, None)

        logger.debug(f"Cache miss for property {property_key}")
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

            # Add work order type data if available
            if 'work_order_types' in property_data:
                total_work_orders = sum(wo['count'] for wo in property_data['work_order_types'])
                work_order_types = []
                for wo_type in property_data['work_order_types']:
                    percentage = (wo_type['count'] / total_work_orders * 100) if total_work_orders > 0 else 0
                    work_order_types.append({
                        'category': wo_type['category'],
                        'count': wo_type['count'],
                        'percentage': percentage
                    })
                metrics_data['work_order_types'] = work_order_types

            metrics = WorkOrderMetrics(**metrics_data)

            # Parse dates
            latest_post_date = self._parse_date(property_data.get('LatestPostDate'))
            period_start = self._parse_date(property_data.get('PeriodStartDate'))
            period_end = self._parse_date(property_data.get('PeriodEndDate'))

            property_model = Property(
                property_key=property_data['PropertyKey'],
                property_name=property_data['PropertyName'],
                property_state_province_code=property_data.get('PropertyStateProvinceCode'),
                total_unit_count=property_data['TotalUnitCount'],
                latest_post_date=latest_post_date,
                status=PropertyStatus.ACTIVE,
                metrics=metrics,
                period_start_date=period_start,
                period_end_date=period_end
            )

            # Cache the converted property with timestamp
            self._conversion_cache[property_key] = property_model
            self._cache_timestamps[property_key] = now
            return property_model

        except ValidationError as e:
            self._handle_error(property_data, 'validation_error', str(e))
        except Exception as e:
            self._handle_error(property_data, 'processing_error', str(e))
        return None

    def _normalize_state_code(self, state_term: str) -> Optional[str]:
        """Convert state name or code to normalized state code"""
        if not state_term:
            return None

        # Clean up the input string
        state_term_lower = state_term.lower().strip()
        logger.debug(f"Attempting to normalize state term: '{state_term}' -> '{state_term_lower}'")

        # Try exact match first
        normalized_code = STATE_SEARCH_MAPPING.get(state_term_lower)
        if normalized_code:
            logger.debug(f"Found exact mapping for '{state_term_lower}' -> '{normalized_code}'")
            return normalized_code

        # Try partial matches
        partial_matches = [(key, value) for key, value in STATE_SEARCH_MAPPING.items()
                           if state_term_lower in key]
        if partial_matches:
            # Use the first partial match
            key, value = partial_matches[0]
            logger.debug(f"Found partial match for '{state_term_lower}' -> '{value}' (from {key})")
            return value

        # Try fuzzy matching if no partial match
        fuzzy_match = get_fuzzy_state_match(state_term_lower)
        if fuzzy_match:
            logger.debug(f"Found fuzzy match for '{state_term_lower}' -> '{fuzzy_match}'")
            return fuzzy_match

        # Log available mappings that are close
        close_matches = [
            (key, value) for key, value in STATE_SEARCH_MAPPING.items()
            if state_term_lower in key or key in state_term_lower
        ]
        if close_matches:
            logger.debug(f"No exact match found for '{state_term_lower}', but found similar: {close_matches}")
        else:
            logger.debug(f"No matches found for '{state_term_lower}'")

        # If not found, return the original term uppercase for code comparison
        return state_term.strip().upper()

    def get_fuzzy_city_matches(self, search_term: str, cutoff: float = 0.6) -> set:
        """Find property keys with cities that fuzzy match the search term"""
        search_term_lower = search_term.lower().strip()

        # Create reverse mapping of cities to keys for easier lookup
        city_to_keys = {}
        for key, city in self._city_index.items():
            if city:  # Only index non-empty cities
                if city in city_to_keys:
                    city_to_keys[city].add(key)
                else:
                    city_to_keys[city] = {key}

        # Try exact substring match first
        exact_matches = {
            key for city, keys in city_to_keys.items()
            for key in keys
            if search_term_lower in city
        }

        if exact_matches:
            logger.debug(f"Found exact city substring matches for '{search_term}': {len(exact_matches)} properties")
            return exact_matches

        # Try fuzzy matching if no exact matches
        matches = get_close_matches(
            search_term_lower,
            city_to_keys.keys(),
            n=5,
            cutoff=cutoff
        )

        if matches:
            fuzzy_matches = set()
            for match in matches:
                fuzzy_matches.update(city_to_keys[match])
            logger.debug(f"Fuzzy matched city '{search_term}' to: {matches}")
            return fuzzy_matches

        return set()

    def _calculate_relevance_score(self,
                                   property_key: int,
                                   search_term: Optional[str],
                                   name_matches: set,
                                   state_matches: set,
                                   city_matches: set,
                                   property_data: Dict) -> float:
        """Calculate a relevance score for a property based on match types"""
        score = 0.0
        score_reasons = []
        property_name = property_data['PropertyName']

        # Only calculate scores if there's a search term
        if search_term:
            search_term_lower = search_term.lower().strip()

            # Name matching score (highest weight)
            if property_key in name_matches:
                property_name_lower = property_name.lower()
                if property_name_lower == search_term_lower:
                    score += 1.0  # Exact name match
                    score_reasons.append("Exact name match (+100)")
                elif search_term_lower in property_name_lower:
                    score += 0.8  # Substring name match
                    score_reasons.append("Substring name match (+80)")
                else:
                    score += 0.6  # Fuzzy name match
                    score_reasons.append("Fuzzy name match (+60)")

            # State matching score
            if property_key in state_matches:
                score += 0.4
                score_reasons.append("State match (+40)")

            # City matching score
            if property_key in city_matches:
                score += 0.3
                score_reasons.append("City match (+30)")

        # Log the scoring details
        if score > 0:
            reasons = ", ".join(score_reasons)
            logger.debug(
                f"Property '{property_name}' (ID: {property_key}) scored {score:.1f} points - Reasons: {reasons}")

        return score

    def search_properties(self,
                          search_term: Optional[str] = None,
                          property_keys: Optional[List[int]] = None,
                          state_province_code: Optional[str] = None,
                          city: Optional[str] = None,
                          include_analytics: bool = False) -> List[Property]:
        """Search properties by name, property keys, state/province code, or city with optional analytics"""
        start_time = time.perf_counter()
        request_start = system_monitor.record_request_start()

        matching_keys = []
        name_matches = set()
        state_matches = set()
        city_matches = set()

        # If searching by specific keys, use those directly
        if property_keys:
            matching_keys = [key for key in property_keys if key in self._raw_cache]
            logger.info(f"Key-based search found {len(matching_keys)} of {len(property_keys)} requested keys")
        else:
            # If we have a search term, use name, state, and city indexes
            search_term_lower = search_term.lower().strip() if search_term else None
            if search_term_lower:
                # Search in property names with fuzzy matching
                name_matches = get_fuzzy_name_matches(search_term, self._name_index)

                # Try to normalize state search term
                normalized_state = self._normalize_state_code(search_term)
                if normalized_state:
                    normalized_state_lower = normalized_state.lower()
                    state_matches = {
                        key for key, state in self._state_index.items()
                        if state and (
                                state == normalized_state_lower or
                                STATE_MAPPING.get(state) == normalized_state
                        )
                    }

                # Search in cities
                city_matches = self.get_fuzzy_city_matches(search_term)

                # Combine matches
                matching_keys = list(name_matches | state_matches | city_matches)
                logger.info(f"Text search '{search_term}' found {len(matching_keys)} matches "
                            f"(Names: {len(name_matches)}, States: {len(state_matches)}, Cities: {len(city_matches)})")

            else:
                matching_keys = list(self._raw_cache.keys())
                logger.info(f"Empty search returning all {len(matching_keys)} properties")

        # Filter by state/province code if provided
        if state_province_code and matching_keys:
            normalized_filter_state = self._normalize_state_code(state_province_code)
            if normalized_filter_state:
                normalized_filter_state_lower = normalized_filter_state.lower()
                matching_keys = [
                    key for key in matching_keys
                    if self._state_index[key] == normalized_filter_state_lower
                ]

        # Filter by city if provided
        if city and matching_keys:
            city_lower = city.lower().strip()
            city_matches = self.get_fuzzy_city_matches(city_lower)
            matching_keys = [key for key in matching_keys if key in city_matches]

        # Calculate relevance scores and sort results
        scored_results: List[Tuple[int, float]] = []
        for key in matching_keys:
            score = self._calculate_relevance_score(
                key,
                search_term,
                name_matches,
                state_matches,
                city_matches,
                self._raw_cache[key]
            )
            scored_results.append((key, score))

        # Sort by relevance score in descending order
        scored_results.sort(key=lambda x: x[1], reverse=True)
        matching_keys = [key for key, _ in scored_results]

        # Convert matching properties
        results = []
        conversion_start = time.perf_counter()
        conversion_errors = 0

        # Track cache hits and misses for monitoring
        cache_hits = 0
        cache_misses = 0
        expired_entries = 0
        now = datetime.now(timezone.utc)

        for key in matching_keys:
            if key in self._conversion_cache and key in self._cache_timestamps:
                cache_timestamp = self._cache_timestamps[key]
                if now - cache_timestamp <= CONVERSION_CACHE_TTL:
                    property = self._conversion_cache[key]
                    cache_hits += 1
                else:
                    expired_entries += 1
                    property_data = self._raw_cache[key]
                    property = self._convert_property(property_data)
                    cache_misses += 1
            else:
                property_data = self._raw_cache[key]
                property = self._convert_property(property_data)
                cache_misses += 1

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

        # Calculate search metrics
        search_time = end_time - start_time
        results_count = len(results)

        # Update monitoring metrics (convert search_time to milliseconds)
        system_monitor.record_search_metrics(
            results_count=results_count,
            query_time=search_time * 1000  # Convert seconds to milliseconds
        )

        # Record route timing
        system_monitor.record_request_end(
            start_time=request_start,
            error=False,
            path='/api/properties/search'
        )

        # Log final performance metrics with cache stats
        conversion_time = end_time - conversion_start
        total_time = end_time - start_time
        success_rate = (len(results) / len(matching_keys)) * 100 if matching_keys else 0
        cache_hit_rate = (cache_hits / (cache_hits + cache_misses) * 100) if (cache_hits + cache_misses) > 0 else 0

        logger.info(
            f"Search completed in {total_time * 1000:.2f}ms (conversion: {conversion_time * 1000:.3f}ms) - "
            f"Converted: {len(results)}/{len(matching_keys)} ({success_rate:.1f}%) - "
            f"Cache hits: {cache_hits}, misses: {cache_misses}, expired: {expired_entries} "
            f"(hit rate: {cache_hit_rate:.1f}%) - "
            f"Cache size: {len(self._conversion_cache)} entries - "
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
                          state_province_code: Optional[str] = None,
                          city: Optional[str] = None,
                          last_updated: Optional[datetime] = None,
                          period_info: Optional[Dict[str, datetime]] = None) -> PropertySearchResult:
        """Get formatted search result with metadata"""
        properties = self.search_properties(
            search_term=search_term,
            property_keys=property_keys,
            state_province_code=state_province_code,
            city=city
        )

        result = PropertySearchResult(
            count=len(properties),
            data=properties,
            last_updated=last_updated or datetime.now(),
            period_info=period_info,
            data_issues=self.data_issues if self.data_issues else None
        )

        return result
