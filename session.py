import secrets
from flask import jsonify, Response, request
from pathlib import Path
from datetime import datetime, timedelta
import logging
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)


def initialize_user_session(request_cookie_session_id: Optional[str] = None) -> Tuple[str, bool]:
    """
    Initialize or validate a user session.

    Args:
        request_cookie_session_id: Optional session ID from request cookie

    Returns:
        Tuple[str, bool]: (session_id, is_new_session)
    """
    try:
        if request_cookie_session_id:
            # Validate existing session
            if is_valid_session(request_cookie_session_id):
                logger.info(f"Using existing session: {request_cookie_session_id}")
                return request_cookie_session_id, False
            else:
                logger.info(f"Existing session invalid, creating new one")

        # Generate new session
        new_session_id = generate_session_id()
        setup_session_directory(new_session_id)
        logger.info(f"Created new session: {new_session_id}")
        return new_session_id, True

    except Exception as e:
        logger.error(f"Error initializing session: {e}")
        # Fallback to new session in case of errors
        fallback_session = generate_session_id()
        setup_session_directory(fallback_session)
        logger.info(f"Created fallback session: {fallback_session}")
        return fallback_session, True


def generate_session_id() -> str:
    """Generate a unique session ID"""
    return secrets.token_hex(16)  # 32 characters


def setup_session_directory(session_id: str) -> Path:
    """
    Create and setup session directory structure.

    Args:
        session_id: The session identifier

    Returns:
        Path: The base session directory path
    """
    session_dir = Path('output') / session_id

    try:
        # Create session directory if it doesn't exist
        session_dir.mkdir(parents=True, exist_ok=True)

        # Create a .session file with timestamp
        session_info_file = session_dir / '.session'
        session_info_file.write_text(datetime.now().isoformat())

        logger.info(f"Setup session directory: {session_dir}")
        return session_dir

    except Exception as e:
        logger.error(f"Error setting up session directory: {e}")
        raise


def is_valid_session(session_id: str) -> bool:
    """
    Check if a session is valid.

    Args:
        session_id: The session identifier

    Returns:
        bool: True if session is valid, False otherwise
    """
    try:
        session_dir = Path('output') / session_id
        session_info_file = session_dir / '.session'

        # Check if session directory and info file exist
        if not (session_dir.exists() and session_info_file.exists()):
            return False

        # Check session age
        session_timestamp = datetime.fromisoformat(session_info_file.read_text())
        session_age = datetime.now() - session_timestamp

        # Session valid if less than 24 hours old
        return session_age < timedelta(hours=24)

    except Exception as e:
        logger.error(f"Error validating session: {e}")
        return False


def get_session_path(session_id: str, request_id: Optional[str] = None) -> Path:
    """
    Get the complete path for a session, optionally with request ID.

    Args:
        session_id: The session identifier
        request_id: Optional request identifier

    Returns:
        Path: The complete session path
    """
    base_path = Path('output') / session_id

    if request_id:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return base_path / request_id / timestamp
    else:
        return base_path


def cleanup_session(session_id: str) -> None:
    """Clean up session files and directories"""
    try:
        session_dir = get_session_path(session_id)
        if not session_dir.exists():
            return

        # Only clean up if session is older than cleanup threshold
        session_info_file = session_dir / '.session'
        if session_info_file.exists():
            session_timestamp = datetime.fromisoformat(session_info_file.read_text())
            age = datetime.now() - session_timestamp

            # Clean up if session is over 10 minutes old
            if age > timedelta(minutes=10):
                import shutil
                shutil.rmtree(session_dir)
                logger.info(f"Cleaned up old session: {session_id}")

    except Exception as e:
        logger.error(f"Error cleaning up session {session_id}: {e}")


# Example usage in app.py
from functools import wraps


def with_session(f):
    """Decorator to ensure endpoint has a valid session"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip session handling for OPTIONS requests
        if request.method == 'OPTIONS':
            return jsonify({'status': 'ok'})

        try:
            # Get session ID from cookie or initialize new session
            cookie_session_id = request.cookies.get('session_id')
            session_id, is_new = initialize_user_session(cookie_session_id)

            # Execute the endpoint function
            response = f(session_id, *args, **kwargs)

            # If response is already a Response object
            if isinstance(response, Response):
                final_response = response
            else:
                final_response = jsonify(response)

            # Set session cookie if it's a new session
            if is_new or not cookie_session_id:
                final_response.set_cookie(
                    'session_id',
                    session_id,
                    max_age=86400,  # 24 hours
                    httponly=False,  # Allow JavaScript access
                    samesite='Lax',
                    secure=False,  # Set to True in production
                    path='/'  # Ensure cookie is available for all paths
                )

            return final_response

        except Exception as e:
            logger.error(f"Session handling error: {e}")
            return jsonify({
                "success": False,
                "message": "Session error occurred"
            }), 500

    return decorated_function


def get_active_sessions() -> List[str]:
    """Get list of active session IDs"""
    try:
        output_dir = Path('output')
        if not output_dir.exists():
            return []

        active_sessions = []
        for session_dir in output_dir.iterdir():
            if not session_dir.is_dir():
                continue

            session_info_file = session_dir / '.session'
            if session_info_file.exists():
                try:
                    session_timestamp = datetime.fromisoformat(session_info_file.read_text())
                    age = datetime.now() - session_timestamp

                    # Consider session active if less than 24 hours old
                    if age < timedelta(hours=24):
                        active_sessions.append(session_dir.name)
                except Exception:
                    continue

        return active_sessions

    except Exception as e:
        logger.error(f"Error getting active sessions: {e}")
        return []


# Add periodic cleanup task
def run_session_cleanup():
    """Run periodic session cleanup"""
    try:
        # Get all session directories
        output_dir = Path('output')
        if not output_dir.exists():
            return

        for session_dir in output_dir.iterdir():
            if not session_dir.is_dir():
                continue

            # Try to clean up session
            cleanup_session(session_dir.name)

    except Exception as e:
        logger.error(f"Error during session cleanup: {e}")
