import threading
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import logging
from logger_config import LogConfig

log_config = LogConfig()
logger = log_config.get_logger('task_manager')


class TaskManager:
    """Manages background tasks with status tracking"""

    def __init__(self, max_concurrent: int = 2):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.max_concurrent = max_concurrent
        self.active_tasks = 0

    def add_task(self, thread: threading.Thread) -> str:
        """Add a new task and return its ID"""
        task_id = str(uuid.uuid4())
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
                "started_at": datetime.now().isoformat() if status == "processing" else None,
                "requested_at": datetime.now().isoformat() if status == "requested" else None,
                "completed_at": None,
                "result": None,
                "error": None
            }

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

        return task_id

    def _transition_task(self, task_id: str, new_status: str, result: Any = None, error: str = None):
        """Internal method to handle task state transitions"""
        start_next = False
        with self.lock:
            if task_id not in self.tasks:
                return False

            task = self.tasks[task_id]
            if task["status"] in ["processing", "requested"]:
                if task["status"] == "processing":
                    self.active_tasks -= 1
                    start_next = True

                task.update({
                    "status": new_status,
                    "completed_at": datetime.now().isoformat(),
                    "result": result,
                    "error": error
                })

        # Start next task outside of lock if needed
        if start_next:
            self._process_next_queued_task()

        return True

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
            next_task["started_at"] = datetime.now().isoformat()
            self.active_tasks += 1

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

    def get_queue_metrics(self) -> Dict[str, Any]:
        """Get statistics about the task queue and positions"""
        with self.lock:
            total_tasks = len(self.tasks)
            requested_tasks = sum(1 for task in self.tasks.values() if task["status"] == "requested")
            running_tasks = self.active_tasks
            completed_tasks = sum(1 for task in self.tasks.values() if task["status"] == "completed")
            failed_tasks = sum(1 for task in self.tasks.values() if task["status"] == "failed")

            # Calculate queue positions for all requested tasks
            queue_positions = {}
            requested_task_list = sorted(
                [(task_id, task_info) for task_id, task_info in self.tasks.items() if
                 task_info["status"] == "requested"],
                key=lambda x: x[1]["requested_at"]
            )

            for position, (task_id, _) in enumerate(requested_task_list):
                queue_positions[task_id] = position + 1  # 1-based position

            return {
                "total_tasks": total_tasks,
                "requested_tasks": requested_tasks,
                "active_tasks": running_tasks,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "max_concurrent": self.max_concurrent,
                "queue_position": queue_positions
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


# Create a global task manager instance with max 3 concurrent tasks
task_manager = TaskManager(max_concurrent=3)
