from flask import request
from functools import wraps
from dataclasses import dataclass
from threading import Semaphore, Lock
from typing import Dict, Optional, Callable, Any
from datetime import datetime


@dataclass
class QueueStats:
    route: str
    queue_size: int
    active_requests: int
    total_processed: int
    avg_processing_time: float
    last_processed: Optional[datetime]


class RouteRequestQueue:
    """Manages request queues for specific routes"""

    def __init__(self, max_concurrent: int = 20):
        self.semaphore = Semaphore(max_concurrent)
        self.stats_lock = Lock()
        self.active_requests = 0
        self.waiting_requests = 0  # Track requests waiting for semaphore
        self.total_processed = 0
        self.total_processing_time = 0
        self.last_processed = None

    def process_request(self, handler: Callable[..., Any]) -> Any:
        """Process a request through the queue with controlled concurrency"""
        start_time = datetime.now()

        with self.stats_lock:
            self.waiting_requests += 1

        try:
            with self.semaphore:
                with self.stats_lock:
                    self.waiting_requests -= 1
                    self.active_requests += 1
                try:
                    return handler()
                finally:
                    with self.stats_lock:
                        self.active_requests -= 1
                        self.total_processed += 1
                        processing_time = (datetime.now() - start_time).total_seconds()
                        self.total_processing_time += processing_time
                        self.last_processed = datetime.now()
        except Exception:
            with self.stats_lock:
                self.waiting_requests -= 1
            raise

    @property
    def avg_processing_time(self) -> float:
        with self.stats_lock:
            if self.total_processed == 0:
                return 0
            return self.total_processing_time / self.total_processed

    @property
    def queue_size(self) -> int:
        """Get current number of requests waiting in queue"""
        with self.stats_lock:
            return self.waiting_requests


class RequestQueueManager:
    """Manages multiple route queues"""

    def __init__(self):
        self.queues: Dict[str, RouteRequestQueue] = {}

    def get_queue(self, route: str, max_concurrent: int = 20) -> RouteRequestQueue:
        if route not in self.queues:
            self.queues[route] = RouteRequestQueue(max_concurrent)
        return self.queues[route]

    def get_stats(self, route: str) -> Optional[QueueStats]:
        if route not in self.queues:
            return None

        queue = self.queues[route]
        return QueueStats(
            route=route,
            queue_size=queue.queue_size,  # Now returns actual waiting requests
            active_requests=queue.active_requests,
            total_processed=queue.total_processed,
            avg_processing_time=queue.avg_processing_time,
            last_processed=queue.last_processed
        )


# Create a global queue manager
queue_manager = RequestQueueManager()


def queue_requests(max_concurrent: int = 20):
    """
    Decorator to queue requests for a specific route

    Usage:
    @app.route('/api/properties/search')
    @queue_requests(max_concurrent=20)
    def search_properties():
        ...
    """

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Get route-specific queue
            route = request.endpoint
            queue = queue_manager.get_queue(route, max_concurrent)

            # Process request through queue
            return queue.process_request(lambda: f(*args, **kwargs))

        return wrapped

    return decorator
