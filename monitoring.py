import psutil
import os
import platform
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging
from collections import deque
import time
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
        self._request_count += 1

        if error:
            self._errors.append(end_time)

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

        return {
            "responseTime": round(avg_response_time, 2),
            "routeResponseTimes": response_times,
            "errorRate": round(error_rate, 2),
            "totalRequests": self._request_count,
            "recentErrors": recent_errors
        }

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
