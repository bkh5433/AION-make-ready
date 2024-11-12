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
from session import with_session, get_session_path, cleanup_session, run_session_cleanup, generate_session_id, \
    setup_session_directory

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5173"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Cookie", "Set-Cookie"],
        "supports_credentials": True,
        "expose_headers": ["Set-Cookie"],
        "max_age": 3600
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
    for record in cache['data']:
        record['ActualOpenWorkOrders_Current'] = record.pop('ActualOpenWorkOrders_Current', 0)
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
    - include_metrics: Whether to include full metrics (default: true)
    """
    logger.info("Starting property search endpoint")
    try:
        search_term = request.args.get('q', None)
        include_metrics = request.args.get('include_metrics', 'true').lower() == 'true'

        logger.debug(f"Search parameters - term: {search_term}, include_metrics: {include_metrics}")

        # Ensure cache is up to date
        if cache['data'] is None or (
                isinstance(cache['last_updated'], datetime) and
                datetime.now() - cache['last_updated'] > timedelta(hours=12)
        ):
            logger.info("Cache needs update, refreshing data")
            update_cache()

        logger.debug(
            f"Cache status - size: {len(cache['data']) if cache['data'] else 0}, last_updated: {cache['last_updated']}")

        # Calculate period dates
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)  # Default 30-day period

        logger.debug(f"Period dates - start: {start_date}, end: {end_date}")

        # Initialize searcher
        logger.info("Initializing PropertySearch")
        searcher = PropertySearch(cache['data'])

        # Get search results
        logger.info("Executing search")
        result = searcher.get_search_result(
            search_term=search_term,
            last_updated=cache['last_updated'],
            period_info={
                'start_date': start_date,
                'end_date': end_date
            }
        )

        logger.info(f"Search complete - found {result.count} properties")

        # Convert to response
        logger.debug("Converting result to JSON")
        response_data = result.model_dump()

        logger.info("Returning search results")
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error in search endpoint: {str(e)}", exc_info=True)
        raise


# In app.py

@app.route('/api/reports/generate', methods=['POST'])
@catch_exceptions
@log_exceptions(logger)
def generate_report():
    """Generate Excel report for selected properties."""
    try:

        # Generate new session ID
        session_id = generate_session_id()
        setup_session_directory(session_id)

        # Get user's output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = get_session_path(session_id) / timestamp
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Generated directory for session {session_id}: {output_dir}")

        # Validate request data
        request_data = request.get_json()
        if not request_data:
            logger.error("No request data provided")
            return {
                "success": False,
                "message": "No request data provided"
            }, 400

        try:
            report_request = ReportGenerationRequest(**request_data)
        except ValidationError as e:
            logger.error(f"Invalid request format: {str(e)}")
            return {
                "success": False,
                "message": f"Invalid request format: {str(e)}"
            }, 400

        # Continue with report generation...
        searcher = PropertySearch(cache['data'])
        properties = searcher.search_properties(property_keys=report_request.properties,
                                                include_analytics=True)

        if not properties:
            logger.warning(f"No properties found for keys: {report_request.properties}")
            return {
                "success": False,
                "message": "No properties found matching the request"
            }, 404

        try:
            # Generate reports
            from data_processing import generate_multi_property_report
            report_files = generate_multi_property_report(
                template_name="break_even_template.xlsx",
                properties=properties,
                output_dir=str(output_dir),
                api_url='http://127.0.0.1:5000/api/data',
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

            response_data = ReportGenerationResponse(
                success=True,
                message="Reports generated successfully",
                output=ReportOutput(
                    directory=str(output_dir.relative_to(Path('output'))),
                    propertyCount=len(properties),
                    files=files,
                    metrics_included=True,
                    period_covered={
                        'start_date': report_request.start_date or (datetime.now() - timedelta(days=30)),
                        'end_date': report_request.end_date or datetime.now()
                    }
                ),
                warnings=[],  # Add any non-critical warnings
                session_id=session_id
            ).model_dump()

            response = jsonify(response_data)
            response.set_cookie(
                'session_id',
                session_id,
                max_age=3600,  # 1 hour - shorter since we only need it for downloads
                httponly=False,
                samesite='Lax',
                secure=False,  # Set to True in production
                path='/'
            )

            return response



        except Exception as e:
            logger.error(f"Error generating reports: {str(e)}", exc_info=True)
            if output_dir.exists():
                shutil.rmtree(output_dir)
            raise

    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": f"Error generating report: {str(e)}"
        }, 500


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
    """Download a report file with enhanced session validation."""
    try:
        # Get session from cookie
        session_id = request.cookies.get('session_id')
        logger.debug(f"Received session ID: {session_id}")  # Debug log
        
        if not session_id:
            logger.error("No session ID provided in cookies")
            return jsonify({
                "success": False,
                "message": "No session ID provided"
            }), 401

        file_path = request.args.get('file')
        if not file_path:
            return jsonify({
                "success": False,
                "message": "Missing file parameter"
            }), 400

        # Construct and verify full path
        full_path = Path('output') / file_path
        if not full_path.exists():
            logger.error(f"File not found: {full_path}")
            return jsonify({
                "success": False,
                "message": "File not found"
            }), 404

        # Security check: ensure file is within session directory
        # try:
        #     session_path = Path('output') / session_id
        #     if not str(full_path).startswith(str(session_path)):
        #         logger.error(f"File access attempt outside session directory: {full_path}")
        #         return jsonify({
        #             "success": False,
        #             "message": "Invalid file access"
        #         }), 403
        # except Exception as e:
        #     logger.error(f"Error validating file path: {str(e)}")
        #     return jsonify({
        #         "success": False,
        #         "message": "Invalid file access"
        #     }), 403

        # Stream the file
        response = send_from_directory(
            directory=str(full_path.parent),
            path=full_path.name,
            as_attachment=True
        )

        # Set cache-control headers
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

        return response

    except Exception as e:
        logger.error(f"Error processing download request: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "message": "Error processing download request"
        }), 500


@app.route('/api/session/end', methods=['POST'])
@catch_exceptions
@log_exceptions(logger)
def end_session():
    """End current session"""
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
            return jsonify({"success": True, "message": "No session to end"})

        cleanup_session(session_id)

        response = jsonify({"success": True, "message": "Session ended"})
        response.delete_cookie('session_id')
        return response

    except Exception as e:
        logger.error(f"Error ending session: {e}")
        return jsonify({
            "success": False,
            "message": "Error ending session"
        }), 500


# Schedule periodic cleanup
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(run_session_cleanup, 'interval', hours=1)
scheduler.start()

if scheduler.state == 1:
    logger.info("Scheduler started successfully.")
else:
    logger.error("Scheduler failed to start.")


if __name__ == '__main__':
    logger.info("Starting application and updating initial cache.")
    app.run(debug=True)
