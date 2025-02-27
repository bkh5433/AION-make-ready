import logging
from typing import Any, Dict, List, Tuple, Optional
from datetime import datetime, timedelta, timezone
from functools import wraps
from dataclasses import dataclass
from logger_config import LogConfig
import threading
import asyncio
import time
from data_retrieval import sql_queries
from data_retrieval.db_connection import DatabaseConnection
from decouple import config

log_config = LogConfig()
logger = log_config.get_logger('cache_module')


@dataclass
class CacheConfig:
    """Configuration for SQL data cache"""
    base_refresh_interval: int = config('CACHE_REFRESH_INTERVAL', cast=int, default=300)
    max_refresh_interval: int = config('CACHE_FORCE_REFRESH', cast=int)
    force_refresh_interval: int = config('CACHE_FORCE_REFRESH', cast=int)
    refresh_timeout: int = config('CACHE_REFRESH_TIMEOUT', cast=int)
    max_retry_attempts: int = config('CACHE_MAX_RETRY_ATTEMPTS', cast=int)
    retry_delay: int = config('CACHE_RETRY_DELAY', cast=int)
    enable_monitoring: bool = config('CACHE_ENABLE_MONITORING', cast=bool, default=True)
    log_refreshes: bool = config('CACHE_LOG_REFRESHES', cast=bool, default=True)
    stale_if_error: bool = config('CACHE_STALE_IF_ERROR', cast=bool, default=True)
    expected_update_time: str = config('CACHE_EXPECTED_UPDATE_TIME', cast=str, default="15:00")
    update_window: int = config('CACHE_UPDATE_WINDOW', cast=int, default=7200)
    version_check_query: str = sql_queries.VERSION_CHECK_QUERY

    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.base_refresh_interval <= 0:
            logger.warning("Base refresh interval must be positive, setting to 30 seconds")
            self.base_refresh_interval = 30

    def get_expected_update_time(self) -> datetime:
        """Get the expected update time in UTC"""
        now = datetime.now(timezone.utc)
        time_parts = self.expected_update_time.split(':')

        logger.debug(f"Parsing expected update time: {self.expected_update_time}")
        logger.debug(f"Current time (UTC): {now}")

        expected_time = now.replace(
            hour=int(time_parts[0]),
            minute=int(time_parts[1]),
            second=0,
            microsecond=0
        )

        logger.debug(f"Calculated expected update time (UTC): {expected_time}")
        return expected_time


class RefreshState:
    """Track refresh state and manage waiters"""
    def __init__(self):
        self.is_refreshing = False
        self.refresh_started: Optional[datetime] = None
        self.refresh_completed: Optional[datetime] = None
        self.error: Optional[str] = None
        self.waiters: int = 0
        self._condition = asyncio.Condition()

    def start_refresh(self):
        """Mark refresh as started"""
        self.is_refreshing = True
        self.refresh_started = datetime.now(timezone.utc)
        self.error = None

    def end_refresh(self):
        """Mark refresh as completed"""
        self.is_refreshing = False
        self.refresh_completed = datetime.now(timezone.utc)

    def set_error(self, error: str):
        """Set error state"""
        self.error = error

    async def wait_for_refresh(self, timeout: float) -> None:
        """Wait for refresh to complete"""
        self.waiters += 1
        try:
            async with self._condition:
                await asyncio.wait_for(self._condition.wait(), timeout)
        finally:
            self.waiters -= 1

    def notify_waiters(self):
        """Notify all waiting tasks that refresh is complete"""
        asyncio.create_task(self._notify_waiters())

    async def _notify_waiters(self):
        """Helper to notify waiters"""
        async with self._condition:
            self._condition.notify_all()


@dataclass
class CacheData:
    """Represents cached data with metadata"""
    data: Any
    last_successful_update: datetime
    last_modified: datetime
    record_count: int
    is_stale: bool = False
    confidence_score: float = 1.0


class ConcurrentSQLCache:
    """
    Thread-safe cache for SQL data with concurrent session handling.
    Implements a non-blocking refresh mechanism with stale data serving.
    """

    def __init__(self, config: CacheConfig):
        self.config = config
        self._primary_cache: Optional[CacheData] = None
        self._fallback_cache: Optional[CacheData] = None
        self._last_refresh: Optional[datetime] = None
        self._refresh_state = RefreshState()
        self._last_data_change = None
        self._next_check_interval = None
        self._update_detected_today = False
        self._current_version = None
        self._import_window_detected = False
        self._last_import_window = None
        self._consecutive_null_count = 0
        self._consecutive_success_count = 0

        # Metrics
        self._access_count = 0
        self._refresh_count = 0
        self._failed_refreshes = 0
        self._concurrent_refreshes_prevented = 0
        self._stale_served_count = 0
        self._total_refresh_time = 0.0
        self._total_wait_time = 0.0
        self._metrics_lock = threading.Lock()

        self._last_version_check: Optional[datetime] = None
        self._version_check_interval: int = 120  # Minimum seconds between version checks
        self._version_check_lock = None  # Initialize as None

    async def _get_lock(self):
        """Get or create the lock in the current event loop"""
        if self._version_check_lock is None:
            self._version_check_lock = asyncio.Lock()
        return self._version_check_lock

    def _detect_import_window(self, version_info: Optional[Dict], error: Optional[str] = None) -> bool:
        """
        Detect if we're in a database import window.
        This can be triggered by either:
        1. Null values in version info (last_modified=None, record_count=0)
        2. Database connection errors that suggest an import is in progress
        3. No version info received at all

        Import window ends only after 2 consecutive successful connections
        """
        # Check for database connection errors first
        if error is not None and any(err in error.lower() for err in [
            "cannot open database",
            "login failed",
            "connection refused",
            "database is not available",
            "(28000)",  # SQL Server login failure code
            "18456"  # SQL Server login failure error number
        ]):
            self._consecutive_null_count += 1
            self._consecutive_success_count = 0
            logger.warning(f"Connection error detected. Consecutive errors: {self._consecutive_null_count}")

            if self._consecutive_null_count >= 3:
                self._import_window_detected = True
                self._last_import_window = datetime.now(timezone.utc)
                logger.warning("Import window detected due to consecutive connection failures")
                logger.warning("Database appears to be in import window due to consecutive connection failures")
                return True

            logger.warning("Database connection error, will retry")
            return False

        # If we have no version info at all, count it as a potential import window indicator
        if version_info is None:
            self._consecutive_null_count += 1
            self._consecutive_success_count = 0
            logger.warning(f"No version info received. Consecutive null responses: {self._consecutive_null_count}")

            if self._consecutive_null_count >= 3:
                self._import_window_detected = True
                self._last_import_window = datetime.now(timezone.utc)
                logger.warning("Import window detected due to consecutive null version info responses")
                return True
            return False

        # If we have version info, check for null values
        if version_info.get('last_modified') is None and version_info.get('record_count', 0) == 0:
            self._consecutive_null_count += 1
            self._consecutive_success_count = 0
            if self._consecutive_null_count >= 3:
                self._import_window_detected = True
                self._last_import_window = datetime.now(timezone.utc)
                logger.warning("Database import window detected - using fallback data")
                return True
        else:
            # Valid data received - increment success counter
            self._consecutive_success_count += 1
            logger.info(f"Valid data received. Consecutive successes: {self._consecutive_success_count}")

            # Only reset counters and end import window after 2 consecutive successes
            if self._consecutive_success_count >= 2:
                if self._consecutive_null_count > 0:
                    logger.info(
                        f"Database access fully restored after {self._consecutive_success_count} successful connections")
                self._consecutive_null_count = 0
                self._consecutive_success_count = 0

                if self._import_window_detected:
                    logger.info("Database import window ended after 2 consecutive successful connections")
                    self._import_window_detected = False

        return self._import_window_detected

    @staticmethod
    def calculate_age_score(age_hours: float, hours_until_update: float) -> float:
        """
        Calculate age score with focus on previous day's data being considered current.
        The database updates daily around 15:00 UTC with previous day's data.
        More lenient scoring up to 48 hours, then gradual degradation.
        """
        if hours_until_update > 0:  # Before update time (before 15:00 UTC)
            if age_hours <= 48:  # Up to two days old is considered current
                return 1.0
            elif age_hours <= 72:  # Three days old starts degradation
                return 0.8
            elif age_hours <= 96:  # Four days old
                return 0.6
            else:  # More than four days old
                return max(0.2, 0.6 - ((age_hours - 96) / 24) * 0.1)  # Degrade by 0.1 per day
        else:  # After update time (after 15:00 UTC)
            if age_hours <= 4:  # Very fresh update
                return 1.0
            elif age_hours <= 48:  # Up to two days old is still good after update
                return 1.0
            elif age_hours <= 72:  # Three days old starts degradation
                return 0.8
            elif age_hours <= 96:  # Four days old
                return 0.6
            else:  # More than four days old
                return max(0.2, 0.6 - ((age_hours - 96) / 24) * 0.1)  # Degrade by 0.1 per day

    @staticmethod
    def calculate_import_score(import_window: bool, consecutive_null_count: int,
                               consecutive_success_count: int) -> float:
        """Calculate import score with gradual recovery"""
        if not import_window:
            return 1.0

        # Gradual degradation based on consecutive nulls
        if consecutive_null_count > 5:
            return 0.2
        elif consecutive_null_count > 3:
            return 0.3

        # Gradual recovery based on consecutive successes
        if consecutive_success_count > 0:
            return min(0.8, 0.4 + (consecutive_success_count * 0.2))

        return 0.4

    @staticmethod
    def calculate_completeness_score(current_count: int, expected_count: int, historical_max: int) -> float:
        """Calculate completeness score with historical context"""
        if expected_count <= 0:
            return 0.0

        ratio = current_count / expected_count
        historical_ratio = current_count / historical_max if historical_max > 0 else 0

        # Severe penalty for less than 80% completeness
        if ratio < 0.8:
            base_score = ratio * 0.5
        elif ratio < 0.9:
            base_score = 0.7
        elif ratio < 0.95:
            base_score = 0.85
        else:
            base_score = 1.0

        # Factor in historical context
        historical_factor = min(1.0, historical_ratio + 0.2)

        return base_score * historical_factor

    @staticmethod
    def calculate_refresh_score(failed_refreshes: int, total_refreshes: int, last_refresh_age: float) -> float:
        """Calculate refresh score with more context"""
        if total_refreshes == 0:
            return 0.5

        # Consider failure rate instead of absolute failures
        failure_rate = failed_refreshes / total_refreshes
        base_score = max(0.2, 1.0 - (failure_rate * 1.5))

        # Factor in refresh age
        if last_refresh_age > 3600:  # More than an hour
            age_penalty = min(0.3, last_refresh_age / 7200)  # Max 30% penalty
            base_score *= (1 - age_penalty)

        return base_score

    def _calculate_confidence_score(self, cache_data: CacheData) -> float:
        """
        Calculate confidence score for cached data based on multiple factors with improved algorithms
        """
        if not cache_data:
            return 0.0

        now = datetime.now(timezone.utc)

        # Calculate age-related metrics
        age_hours = (now - cache_data.last_modified).total_seconds() / 3600
        expected_update_time = self.config.get_expected_update_time()
        hours_until_update = (expected_update_time - now).total_seconds() / 3600 if expected_update_time > now else 24

        # Calculate individual scores
        age_score = self.calculate_age_score(age_hours, hours_until_update)

        import_score = self.calculate_import_score(
            self._import_window_detected,
            self._consecutive_null_count,
            self._consecutive_success_count
        )

        # Get historical max record count
        historical_max = max(
            self._current_version['record_count'] if self._current_version else 0,
            cache_data.record_count,
            getattr(self._fallback_cache, 'record_count', 0) or 0
        )

        completeness_score = self.calculate_completeness_score(
            cache_data.record_count,
            self._current_version['record_count'] if self._current_version else 0,
            historical_max
        )

        # Calculate refresh score with more context
        last_refresh_age = (now - self._last_refresh).total_seconds() if self._last_refresh else float('inf')
        refresh_score = self.calculate_refresh_score(
            self._failed_refreshes,
            self._refresh_count,
            last_refresh_age
        )

        # Determine circumstances for dynamic weighting
        circumstances = {
            'in_business_hours': 8 <= now.hour <= 17,  # 8 AM to 5 PM UTC
            'high_traffic_period': 13 <= now.hour <= 16,  # Peak hours
            'near_update_time': abs(hours_until_update) < 2,  # Within 2 hours of update time
            'post_update_window': -4 <= hours_until_update <= 0,  # Up to 4 hours after expected update
            'pre_update_window': 0 < hours_until_update <= 2,  # Up to 2 hours before expected update
            'data_older_than_48h': age_hours > 48  # Flag for data older than 48 hours
        }

        # Base weights with higher emphasis on age and completeness
        weights = {
            'age': 0.5,  # Maintained high weight for age
            'import': 0.15,  # Maintained import weight
            'completeness': 0.25,  # Maintained completeness weight
            'refresh': 0.1  # Maintained refresh weight
        }

        # Adjust weights based on circumstances
        if circumstances['in_business_hours']:
            if not circumstances['data_older_than_48h']:
                # Normal business hours with current data
                weights['age'] = 0.5
                weights['completeness'] = 0.3
                weights['import'] = 0.15
                weights['refresh'] = 0.05
            else:
                # Increase age importance if data is old during business hours
                weights['age'] = 0.6
                weights['completeness'] = 0.25
                weights['import'] = 0.1
                weights['refresh'] = 0.05

        if circumstances['high_traffic_period']:
            if circumstances['data_older_than_48h']:
                # If data is old during high traffic, emphasize age more
                weights['age'] = 0.6
                weights['completeness'] = 0.25
                weights['import'] = 0.1
                weights['refresh'] = 0.05

        if circumstances['pre_update_window']:
            weights['age'] = 0.55
            weights['completeness'] = 0.25
            weights['import'] = 0.15
            weights['refresh'] = 0.05

        if circumstances['post_update_window']:
            weights['age'] = 0.45
            weights['import'] = 0.35
            weights['completeness'] = 0.15
            weights['refresh'] = 0.05

        # Calculate final score
        scores = {
            'age': age_score,
            'import': import_score,
            'completeness': completeness_score,
            'refresh': refresh_score
        }

        final_score = sum(scores[key] * weights[key] for key in weights)

        # Apply penalties for old data
        if circumstances['data_older_than_48h']:
            if circumstances['in_business_hours'] or circumstances['high_traffic_period']:
                final_score *= 0.95  # 5% penalty for old data during important periods
            else:
                final_score *= 0.98  # 2% penalty for old data during off-hours

        # Log detailed scoring components for debugging
        logger.debug(
            f"Confidence Score Components:\n"
            f"  Age Score ({weights['age'] * 100:.0f}%): {age_score:.2f} "
            f"(Data is {age_hours:.1f} hours old, Hours until update: {hours_until_update:.1f})\n"
            f"  Import Score ({weights['import'] * 100:.0f}%): {import_score:.2f} "
            f"(Import Window: {self._import_window_detected}, Null Count: {self._consecutive_null_count})\n"
            f"  Completeness Score ({weights['completeness'] * 100:.0f}%): {completeness_score:.2f} "
            f"(Records: {cache_data.record_count}/{self._current_version['record_count'] if self._current_version else 0})\n"
            f"  Refresh Score ({weights['refresh'] * 100:.0f}%): {refresh_score:.2f} "
            f"(Failed/Total: {self._failed_refreshes}/{self._refresh_count})\n"
            f"  Circumstances: {circumstances}\n"
            f"  Final Score: {final_score:.2f}"
        )

        return round(final_score, 2)

    async def get_data(self) -> Tuple[Optional[List[Dict]], bool, float]:
        """
        Get cached data with staleness indicator and confidence score.
        Returns: (data, is_stale, confidence_score)
        """
        with self._metrics_lock:
            self._access_count += 1

        if self._refresh_state.is_refreshing:
            try:
                await self._wait_for_refresh()
            except asyncio.TimeoutError:
                if self.config.stale_if_error and self._fallback_cache:
                    logger.warning("Refresh wait timeout, serving fallback data")
                    with self._metrics_lock:
                        self._stale_served_count += 1
                    confidence = self._calculate_confidence_score(self._fallback_cache)
                    return self._fallback_cache.data, True, confidence
                raise

        if self._primary_cache:
            confidence = self._calculate_confidence_score(self._primary_cache)
            return self._primary_cache.data, self.is_stale, confidence
        elif self._fallback_cache:
            confidence = self._calculate_confidence_score(self._fallback_cache)
            return self._fallback_cache.data, True, confidence
        return None, True, 0.0

    async def _wait_for_refresh(self) -> None:
        """Wait for ongoing refresh to complete"""
        with self._metrics_lock:
            self._concurrent_refreshes_prevented += 1

        start_wait = time.time()
        try:
            await self._refresh_state.wait_for_refresh(self.config.refresh_timeout)
        finally:
            with self._metrics_lock:
                self._total_wait_time += time.time() - start_wait

    async def _should_check_version(self) -> bool:
        """Determine if we should perform a version check based on rate limiting"""
        now = datetime.now(timezone.utc)

        # If this is the first check or enough time has passed since last check
        if not self._last_version_check or (
                now - self._last_version_check).total_seconds() >= self._version_check_interval:
            return True

        logger.debug(
            f"Skipping version check - last check was {(now - self._last_version_check).total_seconds():.1f} seconds ago"
        )
        return False

    async def _check_version(self) -> bool:
        """Check if data version has changed with rate limiting and import window detection"""
        lock = await self._get_lock()
        async with lock:
            if not await self._should_check_version():
                return False

            try:
                self._last_version_check = datetime.now(timezone.utc)
                db = DatabaseConnection()
                version_info = await db.fetch_version_info(self.config.version_check_query)

                logger.debug(f"Current stored version info: {self._current_version}")
                logger.debug(f"Received version info: {version_info}")

                if not version_info:
                    logger.warning("No version info returned")
                    # Check for import window with no version info
                    if self._detect_import_window(version_info):
                        return False
                    return False

                # Check for import window with valid version info
                if self._detect_import_window(version_info):
                    return False  # Don't refresh during import window

                if not self._current_version:
                    logger.info(f"Initial version info - PostDate: {version_info['last_modified']}")
                    self._current_version = version_info
                    logger.debug(f"Stored initial version info: {self._current_version}")
                    return True

                # Compare record counts
                if version_info['record_count'] != self._current_version['record_count']:
                    logger.info(
                        f"Record count change detected - Previous: {self._current_version['record_count']}, "
                        f"Current: {version_info['record_count']}"
                    )
                    self._current_version = version_info  # Store new version info
                    logger.debug(f"Updated version info after record count change: {self._current_version}")
                    return True

                # Compare dates
                if version_info['last_modified'] != self._current_version['last_modified']:
                    logger.info(
                        f"Date change detected - Previous: {self._current_version['last_modified']}, Current: {version_info['last_modified']}")
                    self._current_version = version_info  # Store new version info
                    logger.debug(f"Updated version info after date change: {self._current_version}")
                    return True

                logger.debug("No version changes detected")
                return False

            except Exception as e:
                error_str = str(e)
                logger.error(f"Error checking version: {error_str}")
                # Check for import window with error
                if self._detect_import_window(None, error=error_str):
                    return False
                return False

    async def refresh_data(self, fetch_func) -> None:
        """Refresh cache data with import window handling"""
        logger.debug("Refresh data requested")

        if self._refresh_state.is_refreshing:
            logger.debug("Refresh already in progress, waiting...")
            try:
                await self._wait_for_refresh()
                return
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for refresh")
                if not self.config.stale_if_error:
                    raise

        try:
            await self._refresh_data_with_fetch(fetch_func)
        except Exception as e:
            logger.error(f"Error in refresh_data: {str(e)}")
            raise

    async def _refresh_data_with_fetch(self, fetch_func) -> None:
        """Internal method to refresh data with import window handling"""
        if self._refresh_state.is_refreshing:
            return

        needs_refresh = await self._check_version()
        if not needs_refresh:
            logger.debug("Version check indicates no refresh needed or in import window")
            return

        self._refresh_state.start_refresh()
        start_time = time.time()

        try:
            for attempt in range(self.config.max_retry_attempts):
                try:
                    new_data = await fetch_func()
                    if new_data is None:
                        raise ValueError("No data returned from fetch function")

                    now = datetime.now(timezone.utc)
                    logger.debug(f"Creating cache data with version info: {self._current_version}")
                    cache_data = CacheData(
                        data=new_data,
                        last_successful_update=now,
                        last_modified=self._current_version['last_modified'] if self._current_version else now,
                        record_count=len(new_data),
                        is_stale=False,
                        confidence_score=1.0
                    )

                    # Update caches
                    self._fallback_cache = self._primary_cache
                    self._primary_cache = cache_data
                    self._last_refresh = now
                    self._last_data_change = now

                    with self._metrics_lock:
                        self._refresh_count += 1
                        self._total_refresh_time += time.time() - start_time

                    logger.info(f"Cache refreshed successfully with {len(new_data)} records")
                    logger.debug(f"Current version after refresh: {self._current_version}")
                    break

                except Exception as e:
                    if attempt == self.config.max_retry_attempts - 1:
                        raise
                    logger.warning(f"Refresh attempt {attempt + 1} failed: {str(e)}")
                    await asyncio.sleep(self.config.retry_delay)

        except Exception as e:
            with self._metrics_lock:
                self._failed_refreshes += 1
            self._refresh_state.set_error(str(e))
            raise

        finally:
            self._refresh_state.end_refresh()
            self._refresh_state.notify_waiters()

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        with self._metrics_lock:
            now = datetime.now(timezone.utc)
            stats = {
                "status": {
                    "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
                    "cache_age_seconds": (
                        (now - self._last_refresh).total_seconds()
                        if self._last_refresh else None
                    ),
                    "is_stale": self.is_stale,
                    "needs_force_refresh": self.needs_force_refresh,
                    "is_refreshing": self._refresh_state.is_refreshing,
                },
                "data": {
                    "primary_records": len(self._primary_cache.data) if self._primary_cache else 0,
                    "fallback_records": len(self._fallback_cache.data) if self._fallback_cache else 0,
                },
                "performance": {
                    "access_count": self._access_count,
                    "refresh_count": self._refresh_count,
                    "failed_refreshes": self._failed_refreshes,
                    "concurrent_refreshes_prevented": self._concurrent_refreshes_prevented,
                    "stale_data_served_count": self._stale_served_count,
                    "current_waiters": self._refresh_state.waiters,
                },
            }

            if self._refresh_count > 0:
                stats["performance"].update({
                    "avg_refresh_time": self._total_refresh_time / self._refresh_count,
                    "avg_wait_time": (
                        self._total_wait_time / self._concurrent_refreshes_prevented
                        if self._concurrent_refreshes_prevented > 0 else 0
                    ),
                })

            if self._refresh_state.is_refreshing and self._refresh_state.refresh_started:
                stats["status"]["current_refresh_duration"] = (
                    (now - self._refresh_state.refresh_started).total_seconds()
                )

            return stats

    def get_health_details(self) -> Dict:
        """Get detailed health information"""
        now = datetime.now(timezone.utc)
        expected_update = self.config.get_expected_update_time()

        if now > expected_update:
            expected_update += timedelta(days=1)

        time_until_update = (expected_update - now).total_seconds()

        return {
            "cache": {
                "data": {
                    "current_records": len(self._primary_cache) if self._primary_cache else 0,
                    "stale_records": len(self._fallback_cache) if self._fallback_cache else 0
                },
                "performance": self.get_metrics(),
                "status": {
                    "is_refreshing": self._refresh_state.is_refreshing,
                    "is_stale": self.is_stale,
                    "needs_force_refresh": self.needs_force_refresh,
                    "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
                    "cache_age_seconds": (now - self._last_refresh).total_seconds() if self._last_refresh else None,
                    "next_check_interval": self._next_check_interval,  # Add next check interval
                    "time_until_update": time_until_update
                }
            },

        }

    def _calculate_next_check_interval(self) -> int:
        """Optimized interval calculation"""
        now = datetime.now(timezone.utc)
        expected_datetime = self.config.get_expected_update_time()

        if now > expected_datetime:
            expected_datetime = expected_datetime + timedelta(days=1)

        time_until_update = (expected_datetime - now).total_seconds()
        hours_until_update = time_until_update / 3600

        logger.info(
            f"Calculating interval - Current: {now.strftime('%H:%M:%S')} UTC, "
            f"Next update: {expected_datetime.strftime('%H:%M:%S')} UTC, "
            f"Hours until update: {hours_until_update:.2f}"
        )

        if not self._current_version:
            logger.info(f"No version info - using base interval: {self.config.base_refresh_interval} seconds")
            self._next_check_interval = self.config.base_refresh_interval
            return self.config.base_refresh_interval

        last_modified = self._current_version['last_modified']
        last_mod_date = last_modified.date()
        days_old = (now.date() - last_mod_date).days

        logger.debug(f"Data is {days_old} days old")

        # If we're in an import window, use longer interval
        if self._import_window_detected:
            interval = max(self.config.base_refresh_interval * 2, 600)  # At least 10 minutes during import
            logger.info(f"In import window - Using extended interval: {interval / 60:.0f} minutes")
            self._next_check_interval = interval
            return interval

        # If we have yesterday's data (considered fresh)
        if days_old == 1:
            interval = self.config.max_refresh_interval
            logger.info(f"Have fresh data (1 day old) - Using max interval: {interval / 60:.0f} minutes")
            self._next_check_interval = interval
            return interval

        # If data is 2 or more days old, it's considered stale
        if days_old >= 2:
            # If we're outside the update window
            time_to_window = time_until_update - self.config.update_window
            if time_to_window > 0:
                # Use longer interval when far from update window
                interval = min(3600, int(time_to_window / 2))
                logger.info(
                    f"Outside update window with stale data - Using extended interval: {interval / 60:.0f} minutes "
                    f"(Time to window: {time_to_window / 3600:.1f} hours)"
                )
                self._next_check_interval = interval
                return interval

            # If we're in or approaching the update window with stale data
            if -self.config.update_window <= time_until_update <= self.config.update_window:
                logger.info(
                    f"In or approaching update window with stale data (±{self.config.update_window / 3600:.1f} hours) - "
                    f"Using short interval: 5 minutes"
                )
                self._next_check_interval = 300
                return 300

        # Default case - use base interval
        logger.info(
            f"Using base interval: {self.config.base_refresh_interval / 60:.0f} minutes "
            f"(Data age: {days_old} days, Time to update: {hours_until_update:.1f} hours)"
        )
        self._next_check_interval = self.config.base_refresh_interval
        return self.config.base_refresh_interval

    @property
    def is_stale(self) -> bool:
        """Simple staleness check based on hours since last refresh"""
        if not self._last_refresh:
            return True

        now = datetime.now(timezone.utc)
        hours_since_refresh = (now - self._last_refresh).total_seconds() / 3600
        return hours_since_refresh > 12

    @property
    def needs_force_refresh(self) -> bool:
        """Check if cache needs forced refresh"""
        if not self._last_refresh:
            return True
        age = datetime.now(timezone.utc) - self._last_refresh
        return age > timedelta(seconds=self.config.force_refresh_interval)

    @dataclass
    class StalenessInfo:
        """Detailed information about cache staleness"""
        is_stale: bool
        staleness_reason: str
        severity: str  # 'none', 'low', 'medium', 'high', 'critical'
        time_since_refresh: float  # hours
        time_since_update: float  # hours
        next_update_in: float  # hours

    def _get_staleness_info(self) -> StalenessInfo:
        """
        Enhanced staleness check using 12-hour threshold.
        Returns detailed staleness information.
        """
        now = datetime.now(timezone.utc)

        if not self._last_refresh or not self._current_version:
            return self.StalenessInfo(
                is_stale=True,
                staleness_reason="No data available",
                severity="critical",
                time_since_refresh=float('inf'),
                time_since_update=float('inf'),
                next_update_in=0.0
            )

        # Calculate time deltas
        time_since_refresh = (now - self._last_refresh).total_seconds() / 3600
        time_since_update = (now - self._current_version['last_modified']).total_seconds() / 3600
        expected_update_time = self.config.get_expected_update_time()
        hours_until_update = (expected_update_time - now).total_seconds() / 3600 if expected_update_time > now else 24

        # Determine staleness based on 12-hour threshold
        if time_since_refresh <= 12:
            return self.StalenessInfo(
                is_stale=False,
                staleness_reason="Data recently refreshed",
                severity="none",
                time_since_refresh=time_since_refresh,
                time_since_update=time_since_update,
                next_update_in=hours_until_update
            )
        elif time_since_refresh <= 18:  # Between 12 and 18 hours
            return self.StalenessInfo(
                is_stale=True,
                staleness_reason="Data refresh approaching threshold",
                severity="low",
                time_since_refresh=time_since_refresh,
                time_since_update=time_since_update,
                next_update_in=hours_until_update
            )
        elif time_since_refresh <= 24:  # Between 18 and 24 hours
            return self.StalenessInfo(
                is_stale=True,
                staleness_reason="Data refresh overdue",
                severity="medium",
                time_since_refresh=time_since_refresh,
                time_since_update=time_since_update,
                next_update_in=hours_until_update
            )
        else:  # More than 24 hours
            return self.StalenessInfo(
                is_stale=True,
                staleness_reason="Data significantly outdated",
                severity="high",
                time_since_refresh=time_since_refresh,
                time_since_update=time_since_update,
                next_update_in=hours_until_update
            )

    def get_cache_status(self) -> Dict[str, Any]:
        """Get detailed cache status information"""
        staleness_info = self._get_staleness_info()

        return {
            "is_stale": staleness_info.is_stale,
            "staleness_reason": staleness_info.staleness_reason,
            "severity": staleness_info.severity,
            "timing": {
                "hours_since_refresh": round(staleness_info.time_since_refresh, 2),
                "hours_since_update": round(staleness_info.time_since_update, 2),
                "hours_until_next_update": round(staleness_info.next_update_in, 2),
                "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
                "last_update": self._current_version['last_modified'].isoformat() if self._current_version else None,
                "next_expected_update": self.config.get_expected_update_time().isoformat()
            },
            "data_state": {
                "import_window_active": self._import_window_detected,
                "last_import_window": self._last_import_window.isoformat() if self._last_import_window else None,
                "record_count": self._primary_cache.record_count if self._primary_cache else 0,
                "expected_record_count": self._current_version['record_count'] if self._current_version else 0,
                "confidence_score": self._calculate_confidence_score(
                    self._primary_cache) if self._primary_cache else 0.0
            },
            "system_health": {
                "failed_refreshes": self._failed_refreshes,
                "consecutive_null_count": self._consecutive_null_count,
                "consecutive_success_count": self._consecutive_success_count
            }
        }


def with_cache_check(cache_instance):
    """
    Decorator factory for handling cache checks and refreshes.
    Supports concurrent access and stale data handling.
    """

    def decorator(fetch_func):
        @wraps(fetch_func)
        async def wrapper(*args, **kwargs):
            try:
                # Get data and check staleness
                data, is_stale = await cache_instance.get_data()

                # Handle cache miss or force refresh
                if not data or cache_instance.needs_force_refresh:
                    logger.info(
                        "Cache miss or force refresh needed, triggering refresh"
                    )
                    await cache_instance.refresh_data(
                        lambda: fetch_func(*args, **kwargs)
                    )
                    return await cache_instance.get_data()

                # Handle stale data
                if is_stale:
                    # Trigger refresh but don't wait for it
                    asyncio.create_task(
                        cache_instance.refresh_data(
                            lambda: fetch_func(*args, **kwargs)
                        )
                    )

                return data, is_stale

            except Exception as e:
                logger.error(f"Error in cache operation: {str(e)}")
                raise

        return wrapper

    return decorator

