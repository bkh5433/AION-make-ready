from typing import Any, Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from functools import wraps
from dataclasses import dataclass
from logger_config import LogConfig
import threading
import asyncio
import time

log_config = LogConfig()
logger = log_config.get_logger('cache_module')


@dataclass
class CacheConfig:
    """Configuration for SQL data cache"""
    refresh_interval: int = 43200  # 12 hours
    force_refresh_interval: int = 86400  # 24 hours
    refresh_timeout: int = 30  # Maximum seconds to wait for refresh
    max_retry_attempts: int = 3  # Maximum refresh retry attempts
    retry_delay: int = 1  # Seconds between retries
    enable_monitoring: bool = True
    log_refreshes: bool = True
    stale_if_error: bool = True  # Serve stale data on refresh error


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

        # Metrics
        self._access_count = 0
        self._refresh_count = 0
        self._failed_refreshes = 0
        self._concurrent_refreshes_prevented = 0
        self._stale_served_count = 0
        self._total_refresh_time = 0.0
        self._total_wait_time = 0.0
        self._metrics_lock = threading.Lock()

    @property
    def is_stale(self) -> bool:
        """Check if cache needs refresh based on refresh interval"""
        if not self._last_refresh:
            return True
        age = datetime.now() - self._last_refresh
        return age > timedelta(seconds=self.config.refresh_interval)

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

    async def refresh_data(self, fetch_func) -> None:
        """
        Atomically refresh the cache using the provided fetch function.
        Handles concurrent refresh requests and maintains stale data for fallback.
        """
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
        success = False

        try:
            for attempt in range(self.config.max_retry_attempts):
                try:
                    # Fetch new data
                    new_data = await fetch_func()

                    # Backup current data before updating
                    self._stale_data = self._current_data

                    # Update cache atomically
                    self._current_data = new_data
                    self._last_refresh = datetime.now()

                    with self._metrics_lock:
                        self._refresh_count += 1
                        self._total_refresh_time += time.monotonic() - start_time

                    success = True
                    break

                except Exception as e:
                    if attempt == self.config.max_retry_attempts - 1:
                        raise
                    logger.warning(f"Refresh attempt {attempt + 1} failed: {str(e)}")
                    await asyncio.sleep(self.config.retry_delay)

            if self.config.log_refreshes:
                logger.info(
                    f"Cache refreshed successfully: {len(new_data)} records in "
                    f"{time.monotonic() - start_time:.2f} seconds"
                )

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
