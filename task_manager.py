import threading
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from logger_config import LogConfig
from config import Config
from monitoring import SystemMonitor
from queue import Queue, Empty
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
from collections import Counter

log_config = LogConfig()
logger = log_config.get_logger('task_manager')

# Initialize system monitor
system_monitor = SystemMonitor()

class TaskManager:
    """Manages background tasks with status tracking"""

    def __init__(self, max_concurrent: int = Config.MAX_CONCURRENT_TASKS):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.max_concurrent = max_concurrent
        self.active_tasks = 0

        # Task status counters for quick metrics access
        self._status_counts = Counter()

        # Create a queue for monitoring updates with a reasonable size limit
        self._monitoring_queue = Queue(maxsize=1000)

        # Create separate thread pools
        self._monitoring_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="monitoring_pool")
        self._task_pool = ThreadPoolExecutor(max_workers=max_concurrent, thread_name_prefix="task_pool")

        # Start monitoring thread
        self._stop_monitoring = False
        self._monitoring_thread = threading.Thread(target=self._process_monitoring_updates, daemon=True)
        self._monitoring_thread.start()

    def _update_status_counts(self, old_status: Optional[str], new_status: str):
        """Update status counters atomically"""
        if old_status:
            self._status_counts[old_status] -= 1
        self._status_counts[new_status] += 1

    def add_task(self, thread: threading.Thread) -> str:
        """Add a new task and return its ID"""
        task_id = str(uuid.uuid4())
        current_time = datetime.now().isoformat()  # Get timestamp outside lock
        
        with self.lock:
            # Check if we can start the task immediately
            if self.active_tasks < self.max_concurrent:
                status = "processing"
                self.active_tasks += 1
            else:
                status = "requested"

            # Add task to tracking before starting thread
            self.tasks[task_id] = {
                "thread": thread,
                "status": status,
                "started_at": current_time if status == "processing" else None,
                "requested_at": current_time,
                "completed_at": None,
                "result": None,
                "error": None
            }

            # Update counters
            self._update_status_counts(None, status)

            # Get quick metrics snapshot
            metrics = {
                "active_tasks": self.active_tasks,
                "requested_tasks": self._status_counts["requested"],
                "completed_tasks": self._status_counts["completed"],
                "failed_tasks": self._status_counts["failed"]
            }

        # Queue monitoring update outside lock
        self._queue_metrics_update(metrics)

        # Start thread outside of lock if needed
        if status == "processing" and not thread.is_alive():
            try:
                thread.start()
            except RuntimeError as e:
                logger.error(f"Error starting thread for task {task_id}: {e}")
                with self.lock:
                    self.tasks[task_id]["status"] = "failed"
                    self.tasks[task_id]["error"] = str(e)
                    self.active_tasks -= 1
                    self._update_status_counts("processing", "failed")

                    metrics = {
                        "active_tasks": self.active_tasks,
                        "requested_tasks": self._status_counts["requested"],
                        "completed_tasks": self._status_counts["completed"],
                        "failed_tasks": self._status_counts["failed"]
                    }

                self._queue_metrics_update(metrics)

        return task_id

    def get_queue_metrics(self) -> Dict[str, Any]:
        """Get statistics about the task queue and positions"""
        with self.lock:
            # Quick snapshot of current counts
            metrics = {
                "total_tasks": len(self.tasks),
                "requested_tasks": self._status_counts["requested"],
                "active_tasks": self.active_tasks,
                "completed_tasks": self._status_counts["completed"],
                "failed_tasks": self._status_counts["failed"],
                "max_concurrent": self.max_concurrent
            }

            # Only calculate queue positions if there are requested tasks
            if self._status_counts["requested"] > 0:
                # Get requested tasks and their timestamps
                requested_tasks = [
                    (task_id, task["requested_at"])
                    for task_id, task in self.tasks.items()
                    if task["status"] == "requested"
                ]

                # Sort by timestamp
                requested_tasks.sort(key=lambda x: x[1])

                # Create position mapping
                queue_positions = {
                    task_id: pos + 1
                    for pos, (task_id, _) in enumerate(requested_tasks)
                }

                metrics["queue_position"] = queue_positions
            else:
                metrics["queue_position"] = {}

        # Queue monitoring update outside lock
        self._queue_metrics_update(metrics)
        return metrics

    def _transition_task(self, task_id: str, new_status: str, result: Any = None, error: str = None):
        """Internal method to handle task state transitions"""
        start_next = False
        current_time = datetime.now().isoformat()  # Get timestamp outside lock
        
        with self.lock:
            if task_id not in self.tasks:
                return False

            task = self.tasks[task_id]
            old_status = task["status"]

            if old_status in ["processing", "requested"]:
                if old_status == "processing":
                    self.active_tasks -= 1
                    start_next = True

                task.update({
                    "status": new_status,
                    "completed_at": current_time,
                    "result": result,
                    "error": error
                })

                # Update counters
                self._update_status_counts(old_status, new_status)

                # Get quick metrics snapshot
                metrics = {
                    "active_tasks": self.active_tasks,
                    "requested_tasks": self._status_counts["requested"],
                    "completed_tasks": self._status_counts["completed"],
                    "failed_tasks": self._status_counts["failed"]
                }

        # Queue monitoring update outside lock
        self._queue_metrics_update(metrics)

        # Start next task outside of lock if needed
        if start_next:
            self._process_next_queued_task()

        return True

    def _process_monitoring_updates(self):
        """Background thread to process monitoring updates"""
        batch_size = 10  # Process up to 10 updates at once
        batch = []

        while not self._stop_monitoring:
            try:
                # Try to collect a batch of updates
                while len(batch) < batch_size:
                    try:
                        metrics = self._monitoring_queue.get_nowait()
                        batch.append(metrics)
                    except Empty:
                        break

                if not batch:
                    # If no updates, wait for new ones
                    try:
                        metrics = self._monitoring_queue.get(timeout=1.0)
                        batch.append(metrics)
                    except Empty:
                        continue

                if batch:
                    try:
                        # Take the most recent metrics from the batch
                        latest_metrics = batch[-1]

                        # Submit update to monitoring pool
                        future = self._monitoring_pool.submit(
                            system_monitor.update_task_metrics,
                            active=latest_metrics["active_tasks"],
                            queued=latest_metrics["requested_tasks"],
                            completed=latest_metrics["completed_tasks"],
                            failed=latest_metrics["failed_tasks"]
                        )

                        # Mark all batched items as done
                        for _ in batch:
                            try:
                                self._monitoring_queue.task_done()
                            except Exception:
                                pass

                        batch.clear()

                    except Exception as e:
                        logger.error(f"Error submitting monitoring update: {e}")

            except Exception as e:
                logger.error(f"Error in monitoring update thread: {e}")
                batch.clear()  # Clear batch on error

    def _queue_metrics_update(self, metrics: Dict[str, Any]):
        """Queue metrics update to be processed asynchronously"""
        try:
            # Use put_nowait to avoid blocking if queue is full
            self._monitoring_queue.put_nowait(metrics)
        except Exception as e:
            logger.error(f"Error queueing metrics update: {e}")

    def shutdown(self):
        """Cleanup resources on shutdown"""
        self._stop_monitoring = True
        if self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5.0)
        self._monitoring_pool.shutdown(wait=False)
        self._task_pool.shutdown(wait=False)

    def complete_task(self, task_id: str, result: Any = None):
        """Mark a task as completed with its result"""
        self._transition_task(task_id, "completed", result=result)

    def fail_task(self, task_id: str, error: str):
        """Mark a task as failed with error message"""
        self._transition_task(task_id, "failed", error=error)

    def _process_next_queued_task(self):
        """Process the next queued task if capacity allows"""
        next_task = None
        next_task_id = None

        # Get current timestamp outside lock
        current_time = datetime.now().isoformat()

        with self.lock:
            if self.active_tasks >= self.max_concurrent:
                return

            # Find the oldest requested task
            requested_tasks = [(tid, task) for tid, task in self.tasks.items()
                               if task["status"] == "requested"]
            if not requested_tasks:
                return

            # Sort by requested_at timestamp
            requested_tasks.sort(key=lambda x: x[1]["requested_at"])
            next_task_id, next_task = requested_tasks[0]

            # Update status before releasing lock
            next_task["status"] = "processing"
            next_task["started_at"] = current_time
            self.active_tasks += 1

            # Update counters
            self._update_status_counts("requested", "processing")

            # Get metrics snapshot
            metrics = {
                "active_tasks": self.active_tasks,
                "requested_tasks": self._status_counts["requested"],
                "completed_tasks": self._status_counts["completed"],
                "failed_tasks": self._status_counts["failed"]
            }

        # Queue monitoring update outside lock
        if metrics:
            self._queue_metrics_update(metrics)

        # Start thread outside of lock
        if next_task and not next_task["thread"].is_alive():
            try:
                next_task["thread"].start()
            except RuntimeError as e:
                logger.error(f"Error starting requested thread for task {next_task_id}: {e}")
                self._transition_task(next_task_id, "failed", error=str(e))

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a task"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return None

            # Check if thread is still alive for processing tasks
            if task["status"] == "processing":
                thread = task["thread"]
                if not thread.is_alive():
                    # Thread completed but status wasn't updated
                    self._transition_task(task_id, "completed")
                    task = self.tasks[task_id]  # Get updated task info

            return {
                "status": task["status"],
                "started_at": task["started_at"],
                "requested_at": task["requested_at"],
                "completed_at": task["completed_at"],
                "result": task["result"],
                "error": task["error"]
            }

    def cleanup_old_tasks(self, max_age_minutes: int = 10):
        """Clean up tasks older than max_age_minutes"""
        logger.info(f"Starting cleanup of old tasks (max age: {max_age_minutes} minutes)")
        with self.lock:
            now = datetime.now()
            to_remove = []

            for task_id, task in self.tasks.items():
                # For completed or failed tasks, check completion time
                if task["status"] in ["completed", "failed"] and task["completed_at"]:
                    completed_at = datetime.fromisoformat(task["completed_at"])
                    age_minutes = (now - completed_at).total_seconds() / 60
                    if age_minutes > max_age_minutes:
                        to_remove.append(task_id)
                        logger.debug(
                            f"Marking completed/failed task {task_id} for removal (age: {age_minutes:.2f} minutes)")

                # For requested or processing tasks, check creation time
                elif task["status"] in ["requested", "processing"]:
                    creation_time = None
                    if task["started_at"]:
                        creation_time = datetime.fromisoformat(task["started_at"])
                    elif task["requested_at"]:
                        creation_time = datetime.fromisoformat(task["requested_at"])

                    if creation_time:
                        age_minutes = (now - creation_time).total_seconds() / 60
                        if age_minutes > max_age_minutes:
                            to_remove.append(task_id)
                            logger.debug(f"Marking stale task {task_id} for removal (age: {age_minutes:.2f} minutes)")

            for task_id in to_remove:
                del self.tasks[task_id]

            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old/stale tasks")
            else:
                logger.debug("No old tasks to clean up")


# Create a global task manager instance with configured max concurrent tasks from Config.MAX_CONCURRENT_TASKS
task_manager = TaskManager()
