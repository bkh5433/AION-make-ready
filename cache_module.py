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

log_config = LogConfig(default_level=logging.DEBUG)
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


class ConcurrentSQLCache:
    """
    Thread-safe cache for SQL data with concurrent session handling.
    Implements a non-blocking refresh mechanism with stale data serving.
    """

    def __init__(self, config: CacheConfig):
        self.config = config
        self._current_data: Optional[List[Dict]] = None
        self._stale_data: Optional[List[Dict]] = None  # Keep stale data for fallback
        self._last_refresh: Optional[datetime] = None
        self._refresh_state = RefreshState()
        self._last_data_change = None  # Track when data actually changes
        self._next_check_interval = None  # Track the next check interval
        self._update_detected_today = False
        self._current_version = None  # Track database version info

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
        self._version_check_interval: int = 60  # Check version every minute
        self._version_check_lock = asyncio.Lock()  # Add lock for version checks

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

        # If we have today's data
        if days_old == 0:
            interval = self.config.max_refresh_interval
            logger.info(f"Have today's data - Using max interval: {interval / 60:.0f} minutes")
            self._next_check_interval = interval
            return interval

        # If we have stale data but are outside update window
        time_to_window = time_until_update - self.config.update_window

        # If we're outside the update window
        if time_to_window > 0:
            # Use longer interval when far from update window
            interval = min(3600, int(time_to_window / 2))
            logger.info(
                f"Outside update window - Using extended interval: {interval / 60:.0f} minutes "
                f"(Time to window: {time_to_window / 3600:.1f} hours)"
            )
            self._next_check_interval = interval
            return interval

        # If we're in or approaching the update window
        if -self.config.update_window <= time_until_update <= self.config.update_window:
            logger.info(
                f"In or approaching update window (±{self.config.update_window / 3600:.1f} hours) - "
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
        """Enhanced staleness check using dynamic intervals"""
        if not self._last_refresh:
            return True

        now = datetime.now(timezone.utc)
        age = now - self._last_refresh

        # Use the already calculated next check interval
        return age.total_seconds() > self._next_check_interval

    @property
    def needs_force_refresh(self) -> bool:
        """Check if cache needs forced refresh"""
        if not self._last_refresh:
            return True
        age = datetime.now(timezone.utc) - self._last_refresh
        return age > timedelta(seconds=self.config.force_refresh_interval)

    async def get_data(self) -> Tuple[Optional[List[Dict]], bool]:
        """
        Get cached data with staleness indicator.
        Returns: (data, is_stale)
        """
        with self._metrics_lock:
            self._access_count += 1

        # If refresh is in progress, wait for it or return stale data
        if self._refresh_state.is_refreshing:
            try:
                await self._wait_for_refresh()
            except asyncio.TimeoutError:
                if self.config.stale_if_error and self._stale_data:
                    logger.warning("Refresh wait timeout, serving stale data")
                    with self._metrics_lock:
                        self._stale_served_count += 1
                    return self._stale_data, True
                raise

        return self._current_data, self.is_stale

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
        """Determine if we should perform a version check"""
        if not self._last_version_check:
            return True

        age = (datetime.now(timezone.utc) - self._last_version_check).total_seconds()
        should_check = age >= self._version_check_interval

        if not should_check:
            logger.debug(
                f"Skipping version check - last check was {age:.1f} seconds ago "
                f"(interval: {self._version_check_interval}s)"
            )

        return should_check

    async def _check_version(self) -> bool:
        """Check if data version has changed with optimized checking"""
        # Use lock to prevent concurrent version checks
        async with self._version_check_lock:
            if not await self._should_check_version():
                return False

            try:
                self._last_version_check = datetime.now(timezone.utc)

                db = DatabaseConnection()
                version_info = await db.fetch_version_info(self.config.version_check_query)

                if not version_info:
                    logger.warning("Could not fetch version info")
                    return True

                if not self._current_version:
                    logger.info(f"Initial version info - PostDate: {version_info['last_modified']}")
                    self._current_version = version_info
                    self._update_detected_today = (
                            datetime.now(timezone.utc).date() ==
                            version_info['last_modified'].date()
                    )
                    return True

                # Compare record counts first
                if version_info['record_count'] != self._current_version['record_count']:
                    logger.info(
                        f"Record count change detected: {self._current_version['record_count']} -> "
                        f"{version_info['record_count']}"
                    )
                    return True

                # Compare dates
                current_date = version_info['last_modified']
                previous_date = self._current_version['last_modified']

                if current_date != previous_date:
                    logger.info(f"Date change detected - Previous: {previous_date}, Current: {current_date}")
                    return True

                logger.debug(f"No updates needed - Last modified: {current_date}")

                # Update the flag even when no changes detected
                now = datetime.now(timezone.utc)
                self._update_detected_today = (
                        now.date() == version_info['last_modified'].date()
                )
                return False

            except Exception as e:
                logger.error(f"Error checking version: {str(e)}", exc_info=True)
                return True

    async def refresh_data(self, fetch_func) -> None:
        """
        Public method to refresh cache data with custom fetch function.
        Uses non-blocking refresh mechanism.
        """
        logger.debug("Refresh data requested")

        # If refresh is in progress, wait for it
        if self._refresh_state.is_refreshing:
            logger.debug("Refresh already in progress, waiting...")
            try:
                await self._wait_for_refresh()
                return
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for refresh")
                if not self.config.stale_if_error:
                    raise

        # Start refresh
        try:
            await self._refresh_data_with_fetch(fetch_func)
        except Exception as e:
            logger.error(f"Error in refresh_data: {str(e)}")
            raise

    async def _refresh_data_with_fetch(self, fetch_func) -> None:
        """Internal method to refresh data with provided fetch function"""
        if self._refresh_state.is_refreshing:
            logger.debug("Refresh already in progress")
            return

        # Check version first and get version info
        needs_refresh = await self._check_version()
        if not needs_refresh:
            logger.debug("Version check indicates no refresh needed")
            # Update the flag here even if we don't need a refresh
            now = datetime.now(timezone.utc)
            if self._current_version and self._current_version['last_modified']:
                self._update_detected_today = (
                        now.date() == self._current_version['last_modified'].date()
                )
            return

        self._refresh_state.start_refresh()
        start_time = time.time()

        try:
            # Attempt to refresh data with retries
            for attempt in range(self.config.max_retry_attempts):
                try:
                    # Fetch data using the version info we already have
                    new_data = await fetch_func()
                    if new_data is None:
                        raise ValueError("No data returned from fetch function")
                    logger.debug(f"Fetched new data with {len(new_data)} records")

                    # Update cache data
                    self._stale_data = self._current_data
                    self._current_data = new_data
                    self._last_refresh = datetime.now(timezone.utc)
                    self._last_data_change = self._last_refresh

                    # Update the today's update flag
                    self._update_detected_today = (
                            datetime.now(timezone.utc).date() ==
                            self._current_version['last_modified'].date()
                    )

                    with self._metrics_lock:
                        self._refresh_count += 1
                        self._total_refresh_time += time.time() - start_time

                    logger.info(f"Cache refreshed successfully with {len(new_data)} records")
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
                    "current_records": len(self._current_data) if self._current_data else 0,
                    "stale_records": len(self._stale_data) if self._stale_data else 0,
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
                    "current_records": len(self._current_data) if self._current_data else 0,
                    "stale_records": len(self._stale_data) if self._stale_data else 0
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

