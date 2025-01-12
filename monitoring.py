import psutil
import os
import platform
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging
from collections import deque
import time
import statistics
from logger_config import LogConfig

log_config = LogConfig()
logger = log_config.get_logger('system_monitor')

# Define essential routes to track
ESSENTIAL_ROUTES = {
    '/api/properties/search': 'search',
    '/api/reports/generate': 'generation',
    '/api/data': 'data_fetch'
}

class SystemMonitor:
    def __init__(self):
        self.logger = logger
        self._start_time = datetime.now()
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
        self._search_results_count = deque(maxlen=100)  # Track number of results per search
        self._search_query_times = deque(maxlen=100)  # Track query execution times

    def record_request_start(self) -> float:
        """Record the start time of a request"""
        return time.time()

    def record_request_end(self, start_time: float, error: bool = False, path: str = None):
        """Record the end time of a request and calculate metrics"""
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds

        # Determine route category
        route_category = 'other'
        if path:
            route_category = ESSENTIAL_ROUTES.get(path, 'other')

        # Record response time for the appropriate category
        self._response_times[route_category].append(response_time)
        self._route_counts[route_category] += 1
        self._request_count += 1

        if error:
            self._errors.append(end_time)

    def update_task_metrics(self, active: int, queued: int, completed: int, failed: int):
        """Update task manager metrics"""
        self._active_tasks = active
        self._queued_tasks = queued
        self._completed_tasks = completed
        self._failed_tasks = failed

    def record_search_metrics(self, results_count: int, query_time: float):
        """Record additional search-specific metrics"""
        self._search_results_count.append(results_count)
        self._search_query_times.append(query_time)

    def _calculate_percentile(self, data: deque, percentile: float) -> float:
        """Calculate percentile from deque data"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile)
        return sorted_data[index]

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        now = time.time()
        hour_ago = now - 3600  # 1 hour ago

        # Calculate average response time for each category
        response_times = {}
        for category, times in self._response_times.items():
            if times:
                avg_time = sum(times) / len(times)
                response_times[category] = round(avg_time, 2)
            else:
                response_times[category] = 0

        # Calculate overall average for essential routes only
        essential_times = []
        for category in ['search', 'generation', 'data_fetch']:
            essential_times.extend(self._response_times[category])

        avg_response_time = 0
        if essential_times:
            avg_response_time = sum(essential_times) / len(essential_times)

        # Calculate error rate for the last hour
        recent_errors = sum(1 for error_time in self._errors if error_time > hour_ago)
        error_rate = (recent_errors / self._request_count * 100) if self._request_count > 0 else 0

        # Enhanced metrics
        metrics = {
            "responseTime": round(avg_response_time, 2),
            "routeResponseTimes": response_times,
            "errorRate": round(error_rate, 2),
            "totalRequests": self._request_count,
            "recentErrors": recent_errors,

            # Add enhanced metrics while maintaining backward compatibility
            "routeCounts": self._route_counts,

            # Enhanced search metrics
            "searchMetrics": {
                "count": self._route_counts['search'],
                "avgResultsCount": round(
                    statistics.mean(self._search_results_count) if self._search_results_count else 0, 2),
                "avgQueryTime": round(statistics.mean(self._search_query_times) if self._search_query_times else 0, 2),
                "p95QueryTime": round(self._calculate_percentile(self._search_query_times, 0.95), 2),
                "maxQueryTime": round(max(self._search_query_times) if self._search_query_times else 0, 2),
                "minQueryTime": round(min(self._search_query_times) if self._search_query_times else 0, 2)
            },

            # Task manager metrics for report generation
            "taskMetrics": {
                "activeTasks": self._active_tasks,
                "queuedTasks": self._queued_tasks,
                "completedTasks": self._completed_tasks,
                "failedTasks": self._failed_tasks,
                "successRate": round((self._completed_tasks / (self._completed_tasks + self._failed_tasks) * 100) if (
                                                                                                                                 self._completed_tasks + self._failed_tasks) > 0 else 100,
                                     2)
            }
        }

        return metrics

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
