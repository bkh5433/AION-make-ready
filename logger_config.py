import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
import os
import sys
import traceback
from typing import Optional, Dict, Any
from functools import wraps


class ContextFormatter(logging.Formatter):
    """Custom formatter that includes code context"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with additional context"""
        # Get the original formatting
        message = super().format(record)

        # Add code context for errors and exceptions
        if record.levelno >= logging.ERROR:
            if record.exc_info:
                # If we have an exception, format it with full traceback
                exc_type, exc_value, exc_traceback = record.exc_info

                # Get the full traceback
                tb_lines = traceback.extract_tb(exc_traceback)

                # Format each frame in the traceback
                frames = []
                for filename, line_num, func_name, code_line in tb_lines:
                    # Make the path relative to make it more readable
                    try:
                        rel_path = Path(filename).relative_to(Path.cwd())
                    except ValueError:
                        rel_path = filename

                    frames.append(f"\n    File '{rel_path}', line {line_num}, in {func_name}")
                    if code_line:
                        frames.append(f"        {code_line}")

                # Add the exception type and message
                exc_msg = str(exc_value)
                traceback_text = "".join(frames)
                message = f"{message}\nTraceback (most recent call last):{traceback_text}\n{exc_type.__name__}: {exc_msg}"

            else:
                # For errors without exceptions, add the code location
                frame = sys._getframe()
                while frame:
                    if frame.f_code.co_filename != __file__:
                        break
                    frame = frame.f_back

                if frame:
                    filename = frame.f_code.co_filename
                    try:
                        rel_path = Path(filename).relative_to(Path.cwd())
                    except ValueError:
                        rel_path = filename

                    line_num = frame.f_lineno
                    func_name = frame.f_code.co_name

                    # Try to get the actual line of code
                    try:
                        with open(filename, 'r') as f:
                            lines = f.readlines()
                            code_line = lines[line_num - 1].strip()
                            message = f"{message}\nLocation: File '{rel_path}', line {line_num}, in {func_name}\n    {code_line}"
                    except:
                        message = f"{message}\nLocation: File '{rel_path}', line {line_num}, in {func_name}"

        return message


class LogConfig:
    """Centralized logging configuration with enhanced error tracking"""

    def __init__(self, logs_dir: str = "logs", default_level: int = logging.DEBUG):
        self.logs_dir = Path(logs_dir)
        self.default_level = default_level
        self._ensure_log_directory()

        # Configure root logger
        self.configure_root_logger()

    def _ensure_log_directory(self) -> None:
        """Ensure the logs directory exists"""
        if not self.logs_dir.exists():
            self.logs_dir.mkdir(parents=True)

    def configure_root_logger(self) -> None:
        """Configure the root logger with default settings"""
        root_logger = logging.getLogger()
        root_logger.setLevel(self.default_level)

        # Remove any existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Add console handler with context formatter
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.default_level)
        console_handler.setFormatter(ContextFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        root_logger.addHandler(console_handler)

    def get_logger(self,
                   name: str,
                   filename: Optional[str] = None,
                   max_bytes: int = 10_485_760,  # 10MB
                   backup_count: int = 5,
                   level: Optional[int] = None) -> logging.Logger:
        """
        Get a logger with the specified name and configuration

        Args:
            name: Logger name
            filename: Optional specific filename, defaults to name
            max_bytes: Maximum size of each log file
            backup_count: Number of backup files to keep
            level: Optional specific logging level
        """
        logger = logging.getLogger(name)
        logger.setLevel(level or self.default_level)

        # Remove any existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Use name as filename if not specified
        if filename is None:
            filename = f"{name.lower().replace('.', '_')}.log"

        # Create rotating file handler with context formatter
        file_handler = logging.handlers.RotatingFileHandler(
            filename=self.logs_dir / filename,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(ContextFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(file_handler)

        return logger


def log_exceptions(logger: logging.Logger):
    """Decorator to automatically log exceptions with full context"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Exception in {func.__name__}", exc_info=True)
                raise

        return wrapper

    return decorator


# Example usage
if __name__ == "__main__":
    # Initialize logging configuration
    log_config = LogConfig()
    logger = log_config.get_logger("example")


    # Example function with error logging
    @log_exceptions(logger)
    def divide_numbers(a: int, b: int) -> float:
        return a / b


    # Example usage that will generate an error with context
    try:
        result = divide_numbers(10, 0)
    except Exception as e:
        logger.error("Failed to divide numbers", exc_info=True)


    # Example of logging an error without an exception
    def process_data(data: Dict[str, Any]) -> None:
        if not isinstance(data, dict):
            logger.error(f"Invalid data type: {type(data)}")
            return


    process_data("not a dict")  # This will log the error with code context
