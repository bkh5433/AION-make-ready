# session.py

import secrets
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def generate_session_id() -> str:
    """Generate a unique session ID."""
    return secrets.token_hex(6)  # 12 characters


def get_user_output_dir(session_id: str, request_id: Optional[str] = None) -> Path:
    """
    Get the output directory for the current session and timestamp.

    Args:
        session_id (str): The user's session ID
        request_id (Optional[str]): Optional request ID for separate request directories

    Returns:
        Path: The complete output directory path
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if request_id:
        # If request_id is provided, use a three-level structure
        return Path('output') / session_id / request_id / timestamp
    else:
        # Otherwise use a two-level structure
        return Path('output') / session_id / timestamp


def ensure_session_dirs(output_dir: Path) -> None:
    """
    Ensure all necessary directories exist.

    Args:
        output_dir (Path): The directory path to create
    """
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory structure: {output_dir}")
    except Exception as e:
        logger.error(f"Error creating directory structure: {e}")
        raise


def cleanup_old_session_files(session_id: str, max_age_hours: int = 24) -> None:
    """
    Clean up old files from the session directory.

    Args:
        session_id (str): The session ID to clean up
        max_age_hours (int): Maximum age of files in hours before cleanup
    """
    session_dir = Path('output') / session_id
    if not session_dir.exists():
        return

    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

    try:
        for path in session_dir.rglob('*'):
            if path.is_file():
                file_time = datetime.fromtimestamp(path.stat().st_mtime)
                if file_time < cutoff_time:
                    path.unlink()
                    logger.info(f"Removed old file: {path}")

        # Clean up empty directories
        for path in sorted(session_dir.rglob('*'), reverse=True):
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()
                logger.info(f"Removed empty directory: {path}")

    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
