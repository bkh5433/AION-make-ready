from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory, after_this_request, send_file
import shutil
import time
import os
import io
import zipfile
from werkzeug.wsgi import FileWrapper
from flask_cors import CORS
from datetime import datetime, timedelta
from models.models import *
from functools import wraps
from typing import Dict, List, Optional, Union
from pydantic import ValidationError
from property_search import PropertySearch
from logger_config import LogConfig, log_exceptions
from session import generate_session_id, get_user_output_dir, cleanup_old_session_files, \
    ensure_session_dirs

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5173"],  # Vite's default port
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": True,  # Allow credentials
        "expose_headers": ["Set-Cookie"]  # Expose Set-Cookie header
    }
})

# Setup logging
log_config = LogConfig()
logger = log_config.get_logger('api')

# In-memory cache with type hints
cache: Dict[str, Optional[Union[List[Dict], datetime]]] = {
    'data': None,
    'last_updated': None
}


def catch_exceptions(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error occurred: {str(e)}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": "An internal error occurred. Please try again later."
            }), 500

    return wrapper


def update_cache():
    from data_retrieval import sql_queries
    global cache
    logger.info("Updating cache with new data.")
    cache['data'] = sql_queries.fetch_make_ready_data().to_dict(orient='records')
    cache['last_updated'] = datetime.now()
    logger.info("Cache updated successfully.")


@app.route('/api/data', methods=['GET'])
@catch_exceptions
@log_exceptions(logger)
def get_make_ready_data():
    logger.info("GET /api/data endpoint accessed.")
    if cache['data'] is None or (isinstance(cache['last_updated'], datetime) and
                                 datetime.now() - cache['last_updated'] > timedelta(hours=12)):
        logger.info("Cache is empty or outdated. Updating cache.")
        update_cache()

    logger.info("Returning data from cache.")
    return jsonify({
        "status": "success",
        "data": cache['data'],
        "total_records": len(cache['data']) if cache['data'] is not None else 0,
        "last_updated": cache['last_updated'].isoformat() if isinstance(cache['last_updated'], datetime) else None
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    logger.info("GET /api/health endpoint accessed.")
    return jsonify({"status": "healthy"}), 200


@app.route('/api/properties/search', methods=['GET'])
@catch_exceptions
@log_exceptions(logger)
def search_properties():
    """
    Search properties by name.
    Query parameter:
    - q: Search term for property name (optional)
    """
    search_term = request.args.get('q', None)

    # Ensure cache is up to date
    if cache['data'] is None or (
            isinstance(cache['last_updated'], datetime) and
            datetime.now() - cache['last_updated'] > timedelta(hours=12)
    ):
        update_cache()

    # Use PropertySearch class
    searcher = PropertySearch(cache['data'])
    result = searcher.get_search_result(
        search_term=search_term,
        last_updated=cache['last_updated']
    )

    return jsonify(result.model_dump())


# In app.py

@app.route('/api/reports/generate', methods=['POST'])
@catch_exceptions
@log_exceptions(logger)
def generate_report():
    """Generate Excel report for selected properties."""
    try:
        # Get or create session ID
        session_id = request.cookies.get('session_id')
        if not session_id:
            session_id = generate_session_id()
            logger.info(f"Generated new session ID: {session_id}")
        else:
            logger.info(f"Using existing session ID: {session_id}")

        # Clean up any old files for this session
        cleanup_old_session_files(session_id)

        # Get user's output directory - simpler version without request_id
        output_dir = get_user_output_dir(session_id)
        ensure_session_dirs(output_dir)  # Make sure directories exist

        logger.info(f"Generated output directory: {output_dir}")

        # Validate request data
        request_data = request.get_json()
        if not request_data:
            logger.error("No request data provided")
            return jsonify({
                "success": False,
                "message": "No request data provided"
            }), 400

        try:
            report_request = ReportGenerationRequest(**request_data)
        except ValidationError as e:
            logger.error(f"Invalid request format: {str(e)}")
            return jsonify({
                "success": False,
                "message": f"Invalid request format: {str(e)}"
            }), 400

        # Continue with report generation...
        searcher = PropertySearch(cache['data'])
        properties = searcher.search_properties(property_keys=report_request.properties)

        if not properties:
            logger.warning(f"No properties found for keys: {report_request.properties}")
            return jsonify({
                "success": False,
                "message": "No properties found matching the request"
            }), 404

        try:
            # Generate reports
            from data_processing import generate_multi_property_report
            report_files = generate_multi_property_report(
                template_name="break_even_template.xlsx",
                properties=properties,
                output_dir=str(output_dir),
                api_url='http://127.0.0.1:5000/api/data'
            )

            # Process files
            files = []
            for file_path in report_files:
                try:
                    path = Path(file_path)
                    if not path.is_absolute():
                        path = Path.cwd() / path
                    rel_path = path.relative_to(Path.cwd() / 'output')
                    files.append(str(rel_path))
                except Exception as e:
                    logger.error(f"Error processing file path {file_path}: {e}")
                    continue

            logger.info(f"Generated files: {files}")

            # Create response
            response = jsonify(ReportGenerationResponse(
                success=True,
                message="Reports generated successfully",
                output=ReportOutput(
                    directory=str(output_dir.relative_to(Path('output'))),
                    propertyCount=len(properties),
                    files=files
                )
            ).model_dump())

            # Set cookie
            response.set_cookie(
                'session_id',
                session_id,
                max_age=86400,  # 24 hours
                httponly=True,
                samesite='Lax',
                secure=False  # Set to True in production with HTTPS
            )

            logger.info(f"Set session cookie: {session_id}")
            return response

        except Exception as e:
            logger.error(f"Error generating reports: {str(e)}", exc_info=True)
            if output_dir.exists():
                shutil.rmtree(output_dir)
            raise

    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Error generating report: {str(e)}"
        }), 500


@app.route('/api/refresh', methods=['POST'])
@catch_exceptions
@log_exceptions(logger)
def refresh_data():
    logger.info("POST /api/refresh endpoint accessed. Refreshing data.")
    update_cache()
    logger.info("Data refreshed successfully.")
    return jsonify({"status": "success", "message": "Data refreshed successfully"})


def cleanup_empty_directory(directory: Path):
    """Clean up directory if empty after file removal."""
    try:
        # Only remove directory if it's empty and not the root output directory
        if directory.exists() and directory.is_dir():
            remaining_files = list(directory.glob('*'))
            if not remaining_files and 'output' in directory.parts:
                shutil.rmtree(directory)
                logger.info(f"Cleaned up empty directory: {directory}")
    except Exception as e:
        logger.error(f"Error cleaning up directory {directory}: {str(e)}", exc_info=True)


def create_zip_file(files, base_dir: Path) -> io.BytesIO:
    """Create a ZIP file in memory from multiple files."""
    memory_file = io.BytesIO()

    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            # Ensure path is a Path object
            file_path = Path(file_path)
            full_path = base_dir / file_path.name

            if full_path.exists():
                # Add file to zip with just its name (no path)
                zf.write(full_path, file_path.name)

    # Seek to start of file for reading
    memory_file.seek(0)
    return memory_file


def cleanup_files_after_zip(files: List[Path], timestamp_dir: Path):
    """Clean up files after they've been zipped."""
    try:
        # Remove individual files
        for file_path in files:
            full_path = timestamp_dir / file_path.name
            if full_path.exists():
                full_path.unlink()
                logger.info(f"Removed file after zipping: {full_path}")

        # Check if directory is empty and remove if it is
        if not any(timestamp_dir.iterdir()):
            timestamp_dir.rmdir()
            logger.info(f"Removed empty directory: {timestamp_dir}")

    except Exception as e:
        logger.error(f"Error during file cleanup: {e}")
        # Don't raise the exception - cleanup failure shouldn't affect download


@app.route('/api/reports/download', methods=['GET'])
@catch_exceptions
@log_exceptions(logger)
def download_report():
    """Download a report file."""
    try:
        # First try to get session ID from cookie
        session_id = request.cookies.get('session_id')

        # If no cookie, try query parameter
        if not session_id:
            session_id = request.args.get('sessionId')

        file_path = request.args.get('file')

        if not session_id or not file_path:
            logger.error(f"Missing parameters - sessionId: {session_id}, file: {file_path}")
            return jsonify({
                "success": False,
                "message": "Missing required parameters"
            }), 400

        # Log the session and file info
        logger.info(f"Download request - Session ID: {session_id}, File: {file_path}")

        # Split the file path into directory and filename
        path_parts = Path(file_path)
        directory = path_parts.parent
        filename = path_parts.name

        # Construct the full directory path
        full_dir_path = Path('output') / directory

        logger.info(f"Looking for file in directory: {full_dir_path}")

        # Verify the directory exists and is within the output directory
        if not full_dir_path.exists() or not full_dir_path.is_dir():
            logger.error(f"Directory not found: {full_dir_path}")
            return jsonify({
                "success": False,
                "message": "File not found"
            }), 404

        # Verify the file exists
        full_file_path = full_dir_path / filename
        if not full_file_path.exists():
            logger.error(f"File not found: {full_file_path}")
            return jsonify({
                "success": False,
                "message": "File not found"
            }), 404

        logger.info(f"Sending file: {full_file_path}")

        # Create response with file
        response = send_from_directory(
            directory=str(full_dir_path),
            path=filename,
            as_attachment=True
        )

        # Ensure the session cookie is included in the response
        response.set_cookie(
            'session_id',
            session_id,
            max_age=86400,  # 24 hours
            httponly=True,
            samesite='Lax',
            secure=False  # Set to True in production with HTTPS
        )

        return response

    except Exception as e:
        logger.error(f"Error processing download request: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "Error processing download request"
        }), 500




if __name__ == '__main__':
    logger.info("Starting application and updating initial cache.")
    app.run(debug=True)
