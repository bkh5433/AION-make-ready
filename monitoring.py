import psutil
import os
import platform
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging
from collections import deque
import time
import statistics
import threading
import traceback
from logger_config import LogConfig

log_config = LogConfig()
logger = log_config.get_logger('system_monitor')

# Define essential routes to track
ESSENTIAL_ROUTES = {
    '/api/properties/search': 'search',
    '/api/reports/generate': 'generation',
    '/api/data': 'data_fetch'
}


class ThreadSafeMonitor:
    """Wrapper for monitoring lock operations"""

    def __init__(self):
        self._lock = threading.RLock()
        self._owner = None
        self._acquire_count = 0

    def acquire(self):
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        # logger.debug(f"Thread {thread_name} ({thread_id}) attempting to acquire lock...")

        acquired = self._lock.acquire(timeout=5)  # 5 second timeout
        if acquired:
            self._owner = thread_id
            self._acquire_count += 1
            # logger.debug(f"Thread {thread_name} ({thread_id}) acquired lock. Count: {self._acquire_count}")
            return True
        else:
            logger.error(
                f"Thread {thread_name} ({thread_id}) failed to acquire lock after 5s. Current owner: {self._owner}")
            logger.error("Stack trace:\n" + ''.join(traceback.format_stack()))
            return False

    def release(self):
        thread_id = threading.get_ident()
        thread_name = threading.current_thread().name
        if self._owner == thread_id:
            self._acquire_count -= 1
            if self._acquire_count == 0:
                self._owner = None
            self._lock.release()
            # logger.debug(f"Thread {thread_name} ({thread_id}) released lock. Count: {self._acquire_count}")
        else:
            logger.error(
                f"Thread {thread_name} ({thread_id}) attempting to release lock it doesn't own! Owner: {self._owner}")
            logger.error("Stack trace:\n" + ''.join(traceback.format_stack()))

class SystemMonitor:
    def __init__(self):
        self.logger = logger
        self._start_time = datetime.now()
        self._monitor = ThreadSafeMonitor()
        
        # Track response times per route
        self._response_times = {
            'search': deque(maxlen=100),
            'generation': deque(maxlen=100),
            'data_fetch': deque(maxlen=100),
            'other': deque(maxlen=100)
        }
        self._errors = deque(maxlen=1000)
        self._request_count = 0

        # Enhanced metrics tracking
        self._route_counts = {
            'search': 0,
            'generation': 0,
            'data_fetch': 0,
            'other': 0
        }

        # Task manager metrics for report generation
        self._active_tasks = 0
        self._queued_tasks = 0
        self._completed_tasks = 0
        self._failed_tasks = 0

        # Search metrics
        self._search_results_count = deque(maxlen=100)
        self._search_query_times = deque(maxlen=100)

    def record_request_start(self) -> float:
        """Record the start time of a request"""
        return time.time()

    def record_request_end(self, start_time: float, error: bool = False, path: str = None):
        """Record the end time of a request and calculate metrics"""
        if not self._monitor.acquire():
            logger.error("Failed to acquire lock for record_request_end")
            return

        try:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000

            route_category = 'other'
            if path:
                route_category = ESSENTIAL_ROUTES.get(path, 'other')

            self._response_times[route_category].append(response_time)
            self._route_counts[route_category] += 1
            self._request_count += 1

            if error:
                self._errors.append(end_time)
        finally:
            self._monitor.release()

    def update_task_metrics(self, active: int, queued: int, completed: int, failed: int):
        """Update task manager metrics"""
        if not self._monitor.acquire():
            logger.error("Failed to acquire lock for update_task_metrics")
            return

        try:
            self._active_tasks = active
            self._queued_tasks = queued
            self._completed_tasks = completed
            self._failed_tasks = failed
        finally:
            self._monitor.release()

    def record_search_metrics(self, results_count: int, query_time: float):
        """Record additional search-specific metrics"""
        if not self._monitor.acquire():
            logger.error("Failed to acquire lock for record_search_metrics")
            return

        try:
            self._search_results_count.append(results_count)
            self._search_query_times.append(query_time)
        finally:
            self._monitor.release()

    def _calculate_percentile(self, data: deque, percentile: float) -> float:
        """Calculate percentile from deque data"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile)
        return sorted_data[index]

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        if not self._monitor.acquire():
            logger.error("Failed to acquire lock for get_performance_metrics")
            return {
                "error": "Failed to acquire lock for metrics collection",
                "timestamp": datetime.now().isoformat()
            }

        try:
            now = time.time()
            hour_ago = now - 3600

            # Make thread-safe copies of all data structures
            response_times = {k: list(v) for k, v in self._response_times.items()}
            route_counts = dict(self._route_counts)
            search_results = list(self._search_results_count)
            search_times = list(self._search_query_times)
            errors = list(self._errors)

            # Calculate metrics using the copies
            response_time_avgs = {}
            for category, times in response_times.items():
                if times:
                    avg_time = sum(times) / len(times)
                    response_time_avgs[category] = round(avg_time, 2)
                else:
                    response_time_avgs[category] = 0

            essential_times = []
            for category in ['search', 'generation', 'data_fetch']:
                essential_times.extend(response_times[category])

            avg_response_time = 0
            if essential_times:
                avg_response_time = sum(essential_times) / len(essential_times)

            recent_errors = sum(1 for error_time in errors if error_time > hour_ago)
            error_rate = (recent_errors / self._request_count * 100) if self._request_count > 0 else 0

            metrics = {
                "responseTime": round(avg_response_time, 2),
                "routeResponseTimes": response_time_avgs,
                "errorRate": round(error_rate, 2),
                "totalRequests": self._request_count,
                "recentErrors": recent_errors,
                "routeCounts": route_counts,
                "searchMetrics": {
                    "count": route_counts['search'],
                    "avgResultsCount": round(
                        statistics.mean(search_results) if search_results else 0, 2),
                    "avgQueryTime": round(statistics.mean(search_times) if search_times else 0, 2),
                    "p95QueryTime": round(self._calculate_percentile(search_times, 0.95), 2),
                    "maxQueryTime": round(max(search_times) if search_times else 0, 2),
                    "minQueryTime": round(min(search_times) if search_times else 0, 2)
                },
                "taskMetrics": {
                    "activeTasks": self._active_tasks,
                    "queuedTasks": self._queued_tasks,
                    "completedTasks": self._completed_tasks,
                    "failedTasks": self._failed_tasks,
                    "successRate": round((self._completed_tasks / (self._completed_tasks + self._failed_tasks) * 100)
                                         if (self._completed_tasks + self._failed_tasks) > 0 else 100, 2)
                }
            }
            return metrics
        except Exception as e:
            logger.error(f"Error collecting metrics: {str(e)}\n{traceback.format_exc()}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        finally:
            self._monitor.release()

    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        memory = psutil.virtual_memory()
        return {
            "total": memory.total,
            "used": memory.used,
            "free": memory.free,
            "usage": memory.percent
        }

    def get_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage statistics"""
        disk = psutil.disk_usage('/')
        return {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "usage": disk.percent
        }

    def get_cpu_usage(self) -> Dict[str, Any]:
        """Get CPU usage statistics"""
        return {
            "usage": psutil.cpu_percent(interval=1),
            "cores": psutil.cpu_count()
        }

    def get_network_info(self) -> Dict[str, Any]:
        """Get network statistics"""
        network = psutil.net_io_counters()
        process = psutil.Process()
        uptime = time.time() - process.create_time()
        return {
            "bytesPerSec": (network.bytes_sent + network.bytes_recv) / uptime,
            "sent": network.bytes_sent,
            "received": network.bytes_recv
        }

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all system metrics"""
        try:
            return {
                "timestamp": datetime.now().isoformat(),
                "memory": self.get_memory_usage(),
                "disk": self.get_disk_usage(),
                "cpu": self.get_cpu_usage(),
                "network": self.get_network_info(),
                "performance": self.get_performance_metrics()
            }
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {str(e)}")
            return {"error": str(e)}
