from typing import Any, Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from functools import wraps
from dataclasses import dataclass
from logger_config import LogConfig
import threading
import asyncio
import time
from data_retrieval import sql_queries

log_config = LogConfig()
logger = log_config.get_logger('cache_module')


@dataclass
class CacheConfig:
    """Configuration for SQL data cache"""
    base_refresh_interval: int = 1800  # 30 minutes for checking updates
    max_refresh_interval: int = 43200  # 12 hours
    force_refresh_interval: int = 86400  # 24 hours
    refresh_timeout: int = 30
    max_retry_attempts: int = 3
    retry_delay: int = 1
    enable_monitoring: bool = True
    log_refreshes: bool = True
    stale_if_error: bool = True
    expected_update_time: str = "10:00"  # Expected daily update time
    update_window: int = 7200  # 2-hour window around expected time (±1 hour)
    version_check_query: str = sql_queries.VERSION_CHECK_QUERY


class RefreshState:
    """Tracks the state of a cache refresh operation"""

    def __init__(self):
        self.is_refreshing = False
        self.refresh_started = None
        self.refresh_completed = None
        self.error = None
        self.waiters = 0
        self.lock = threading.Lock()
        self.refresh_event = asyncio.Event()


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
        self._next_check_interval = config.base_refresh_interval
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

    def _calculate_next_check_interval(self) -> int:
        """Dynamically calculate the next check interval based on patterns"""
        now = datetime.now()
        expected_time = datetime.strptime(self.config.expected_update_time, "%H:%M").time()

        # Convert expected_time to today's datetime
        expected_datetime = datetime.combine(now.date(), expected_time)

        # Calculate time until expected update
        time_until_update = (expected_datetime - now).total_seconds()
        if time_until_update < 0:
            # If we're past today's expected time, look at tomorrow
            expected_datetime = datetime.combine(now.date() + timedelta(days=1), expected_time)
            time_until_update = (expected_datetime - now).total_seconds()

        # Reset the update detection flag at midnight
        if now.hour == 0 and now.minute < 30:
            self._update_detected_today = False

        # If we're within the update window
        if abs(time_until_update) <= self.config.update_window:
            # Check more frequently during the update window
            return min(300, self.config.base_refresh_interval)  # 5 minutes or base interval

        # If we've detected today's update, use longer interval
        if self._update_detected_today:
            return self.config.max_refresh_interval

        # Default to base interval
        return self.config.base_refresh_interval

    @property
    def is_stale(self) -> bool:
        """Enhanced staleness check using dynamic intervals"""
        if not self._last_refresh:
            return True

        now = datetime.now()
        age = now - self._last_refresh

        # Calculate the current appropriate interval
        current_interval = self._calculate_next_check_interval()

        return age.total_seconds() > current_interval

    @property
    def needs_force_refresh(self) -> bool:
        """Check if cache needs forced refresh"""
        if not self._last_refresh:
            return True
        age = datetime.now() - self._last_refresh
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
        start_wait = time.monotonic()
        self._refresh_state.waiters += 1

        try:
            await asyncio.wait_for(
                self._refresh_state.refresh_event.wait(),
                timeout=self.config.refresh_timeout
            )
        finally:
            self._refresh_state.waiters -= 1
            with self._metrics_lock:
                self._total_wait_time += time.monotonic() - start_wait

    async def _check_for_updates(self, db_connection) -> bool:
        """Check if database has been updated without fetching all data."""
        try:
            version_info = await db_connection.fetch_version_info(
                self.config.version_check_query
            )

            if not version_info:
                logger.warning("Could not fetch version info")
                return True

            current_version = {
                'last_modified': version_info['last_modified'],
                'record_count': version_info['record_count']
            }

            if not self._current_version:
                logger.info(f"Initial version info - PostDate: {current_version['last_modified']}")
                self._current_version = current_version
                return True

            needs_update = (
                    current_version['last_modified'] != self._current_version['last_modified'] or
                    current_version['record_count'] != self._current_version['record_count']
            )

            if needs_update:
                logger.info(
                    f"Update detected - New PostDate: {current_version['last_modified']}, "
                    f"Previous PostDate: {self._current_version['last_modified']}, "
                    f"Record count change: {self._current_version['record_count']} -> "
                    f"{current_version['record_count']}"
                )
            else:
                logger.debug(
                    f"No updates detected - Current PostDate: {current_version['last_modified']}"
                )

            return needs_update

        except Exception as e:
            logger.error(f"Error checking for updates: {str(e)}")
            return True

    async def refresh_data(self, fetch_func) -> None:
        """Enhanced refresh function with efficient update detection"""
        try:
            # Check if refresh is already in progress
            with self._refresh_state.lock:
                if self._refresh_state.is_refreshing:
                    with self._metrics_lock:
                        self._concurrent_refreshes_prevented += 1
                    logger.debug("Refresh already in progress, waiting...")
                    try:
                        await self._wait_for_refresh()
                        return
                    except asyncio.TimeoutError:
                        logger.error("Timeout waiting for refresh to complete")
                        raise

                self._refresh_state.is_refreshing = True
                self._refresh_state.refresh_started = datetime.now()
                self._refresh_state.refresh_event.clear()

            start_time = time.monotonic()

            try:
                # Create database connection for version check
                from data_retrieval.db_connection import DatabaseConnection
                db = DatabaseConnection()

                # Check if we actually need to update
                needs_update = await self._check_for_updates(db)

                if not needs_update:
                    logger.info("No database updates detected, skipping refresh")
                    self._next_check_interval = self._calculate_next_check_interval()
                    return

                # Proceed with full data fetch if updates are detected
                for attempt in range(self.config.max_retry_attempts):
                    try:
                        new_data = await fetch_func()

                        # Update version info and cache data
                        version_info = await db.fetch_version_info(
                            self.config.version_check_query
                        )
                        self._current_version = {
                            'last_modified': version_info['last_modified'],
                            'record_count': version_info['record_count']
                        }

                        # Backup current data before updating
                        self._stale_data = self._current_data
                        self._current_data = new_data
                        self._last_refresh = datetime.now()
                        self._last_data_change = datetime.now()
                        self._update_detected_today = True

                        with self._metrics_lock:
                            self._refresh_count += 1
                            self._total_refresh_time += time.monotonic() - start_time

                        break

                    except Exception as e:
                        if attempt == self.config.max_retry_attempts - 1:
                            raise
                        logger.warning(f"Refresh attempt {attempt + 1} failed: {str(e)}")
                        await asyncio.sleep(self.config.retry_delay)

                # Calculate next check interval
                self._next_check_interval = self._calculate_next_check_interval()
                logger.info(f"Next check scheduled in {self._next_check_interval} seconds")

            except Exception as e:
                with self._metrics_lock:
                    self._failed_refreshes += 1
                self._refresh_state.error = str(e)
                logger.error(f"Failed to refresh cache: {str(e)}")
                raise

            finally:
                # Reset refresh state and notify waiters
                with self._refresh_state.lock:
                    self._refresh_state.is_refreshing = False
                    self._refresh_state.refresh_completed = datetime.now()
                self._refresh_state.refresh_event.set()

        except Exception as e:
            logger.error(f"Error in refresh_data: {str(e)}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        with self._metrics_lock:
            stats = {
                "status": {
                    "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
                    "cache_age_seconds": (
                        (datetime.now() - self._last_refresh).total_seconds()
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

            if self._refresh_state.is_refreshing:
                stats["status"]["current_refresh_duration"] = (
                    (datetime.now() - self._refresh_state.refresh_started).total_seconds()
                    if self._refresh_state.refresh_started else None
                )

            return stats


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
