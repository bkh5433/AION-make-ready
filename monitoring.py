import psutil
import os
import platform
from datetime import datetime
from typing import Dict, Any
import logging


class SystemMonitor:
    def __init__(self):
        self.logger = logging.getLogger('system_monitor')
        self._start_time = datetime.now()

    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        memory = psutil.virtual_memory()
        return {
            "total": self._bytes_to_gb(memory.total),
            "available": self._bytes_to_gb(memory.available),
            "used": self._bytes_to_gb(memory.used),
            "free": self._bytes_to_gb(memory.free),
            "percent": memory.percent
        }

    def get_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage statistics"""
        disk = psutil.disk_usage('/')
        return {
            "total": self._bytes_to_gb(disk.total),
            "used": self._bytes_to_gb(disk.used),
            "free": self._bytes_to_gb(disk.free),
            "percent": disk.percent
        }

    def get_cpu_usage(self) -> Dict[str, Any]:
        """Get CPU usage statistics"""
        return {
            "percent": psutil.cpu_percent(interval=1),
            "cores": {
                "physical": psutil.cpu_count(logical=False),
                "logical": psutil.cpu_count(logical=True)
            },
            "frequency": {
                "current": psutil.cpu_freq().current,
                "min": psutil.cpu_freq().min,
                "max": psutil.cpu_freq().max
            }
        }

    def get_process_info(self) -> Dict[str, Any]:
        """Get current process information"""
        process = psutil.Process(os.getpid())
        return {
            "memory_percent": process.memory_percent(),
            "cpu_percent": process.cpu_percent(interval=1),
            "threads": process.num_threads(),
            "uptime_seconds": (datetime.now() - self._start_time).total_seconds()
        }

    def get_system_info(self) -> Dict[str, Any]:
        """Get general system information"""
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "hostname": platform.node()
        }

    def get_network_info(self) -> Dict[str, Any]:
        """Get network statistics"""
        network_stats = psutil.net_io_counters()
        return {
            "bytes_sent": self._bytes_to_mb(network_stats.bytes_sent),
            "bytes_received": self._bytes_to_mb(network_stats.bytes_recv),
            "packets_sent": network_stats.packets_sent,
            "packets_received": network_stats.packets_recv
        }

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all system metrics"""
        try:
            return {
                "timestamp": datetime.now().isoformat(),
                "memory": self.get_memory_usage(),
                "disk": self.get_disk_usage(),
                "cpu": self.get_cpu_usage(),
                "process": self.get_process_info(),
                "system": self.get_system_info(),
                "network": self.get_network_info()
            }
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {str(e)}")
            return {"error": str(e)}

    @staticmethod
    def _bytes_to_gb(bytes_value: int) -> float:
        """Convert bytes to gigabytes"""
        return round(bytes_value / (1024 ** 3), 2)

    @staticmethod
    def _bytes_to_mb(bytes_value: int) -> float:
        """Convert bytes to megabytes"""
        return round(bytes_value / (1024 ** 2), 2)
