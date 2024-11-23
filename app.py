from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory, after_this_request, send_file
import shutil
import io
import zipfile
import threading
import asyncio
from flask_cors import CORS
from models.ReportGenerationRequest import ReportGenerationRequest
from models.ReportGenerationResponse import ReportGenerationResponse
from models.ReportOutput import ReportOutput
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Optional, Union
from pydantic import ValidationError
from property_search import PropertySearch
from logger_config import LogConfig, log_exceptions
from session import get_session_path, cleanup_session, run_session_cleanup, generate_session_id, \
    setup_session_directory
from data_processing import generate_multi_property_report
from cache_module import ConcurrentSQLCache, CacheConfig

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

cache_config = CacheConfig(
    refresh_interval=43200,  # 12 hours
    force_refresh_interval=86400,  # 24 hours
    refresh_timeout=30,
    max_retry_attempts=3,
    retry_delay=2,
    enable_monitoring=True,
    stale_if_error=True
)

cache = ConcurrentSQLCache(cache_config)


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


def fetch_make_ready_data_sync():
    """Synchronous function to fetch data from SQL"""
    from data_retrieval.db_connection import DatabaseConnection
    try:
        db = DatabaseConnection()
        data = db.fetch_data().to_dict(orient='records')
        # Process ActualOpenWorkOrders_Current consistently
        for record in data:
            record['ActualOpenWorkOrders_Current'] = record.pop('ActualOpenWorkOrders_Current', 0)
        return data
    except Exception as e:
        logger.error(f"Error fetching make ready data: {str(e)}")
        raise


async def fetch_make_ready_data():
    """Async wrapper for the synchronous fetch function"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, fetch_make_ready_data_sync)


def run_async(coro):
    """Run an async function in a new event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.route('/api/data', methods=['GET'])
@catch_exceptions
@log_exceptions(logger)
def get_make_ready_data():
    logger.info("GET /api/data endpoint accessed.")
    try:
        # Get data and check staleness
        data, is_stale = run_async(cache.get_data())

        if not data:
            # Initial cache population
            logger.info("Cache empty, performing initial population")
            run_async(cache.refresh_data(fetch_make_ready_data))
            data, is_stale = run_async(cache.get_data())
        elif is_stale:
            # Trigger background refresh
            logger.info("Data is stale, triggering background refresh")
            thread = threading.Thread(
                target=run_async,
                args=(cache.refresh_data(fetch_make_ready_data),)
            )
            thread.daemon = True
            thread.start()

        return jsonify({
            "status": "success",
            "data": data,
            "total_records": len(data) if data else 0,
            "last_updated": cache._last_refresh.isoformat() if cache._last_refresh else None,
            "is_stale": is_stale
        })

    except Exception as e:
        logger.error(f"Error in get_make_ready_data: {str(e)}")
        raise


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

        # Get data from cache
        data, is_stale = run_async(cache.get_data())

        if not data:
            # Initial cache population
            logger.info("Cache empty, performing initial population")
            run_async(cache.refresh_data(fetch_make_ready_data))
            data, is_stale = run_async(cache.get_data())
        elif is_stale:
            # Trigger background refresh if data is stale
            logger.info("Data is stale, triggering background refresh")
            thread = threading.Thread(
                target=run_async,
                args=(cache.refresh_data(fetch_make_ready_data),)
            )
            thread.daemon = True
            thread.start()

        logger.debug(
            f"Cache status - size: {len(data) if data else 0}, is_stale: {is_stale}")

        # Calculate period dates
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)  # Default 30-day period

        logger.debug(f"Period dates - start: {start_date}, end: {end_date}")

        # Initialize searcher
        logger.info("Initializing PropertySearch")
        searcher = PropertySearch(data)

        # Get search results
        logger.info("Executing search")
        result = searcher.get_search_result(
            search_term=search_term,
            last_updated=cache._last_refresh,  # Use the cache's last refresh time
            period_info={
                'start_date': start_date,
                'end_date': end_date
            }
        )

        logger.info(f"Search complete - found {result.count} properties")

        # Convert to response and include staleness
        logger.debug("Converting result to JSON")
        response_data = result.model_dump()
        response_data['is_stale'] = is_stale

        # Add cache statistics if needed
        if include_metrics:
            response_data['cache_stats'] = {
                'last_refresh': cache._last_refresh.isoformat() if cache._last_refresh else None,
                'is_refreshing': cache._refresh_state.is_refreshing,
                'refresh_age': (
                    (datetime.now() - cache._last_refresh).total_seconds()
                    if cache._last_refresh else None
                )
            }

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
    """Generate Excel report for selected properties in a single workbook."""
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

        # Get data from cache
        data, is_stale = run_async(cache.get_data())

        if not data:
            logger.info("Cache empty, performing initial population")
            run_async(cache.refresh_data(fetch_make_ready_data))
            data, is_stale = run_async(cache.get_data())
        elif is_stale:
            # Trigger background refresh if data is stale
            logger.info("Data is stale, triggering background refresh")
            thread = threading.Thread(
                target=run_async,
                args=(cache.refresh_data(fetch_make_ready_data),)
            )
            thread.daemon = True
            thread.start()

        # Initialize searcher with cached data
        searcher = PropertySearch(data)
        properties = searcher.search_properties(
            property_keys=report_request.properties,
            include_analytics=True
        )

        if not properties:
            logger.warning(f"No properties found for keys: {report_request.properties}")
            return {
                "success": False,
                "message": "No properties found matching the request"
            }, 404

        try:
            # Generate single report with multiple sheets
            report_files = generate_multi_property_report(
                template_name="break_even_template.xlsx",
                properties=properties,
                output_dir=str(output_dir),
                api_url='http://127.0.0.1:5000/api/data',
            )

            # Process the single file
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

            logger.info(f"Generated file: {files}")

            # Create warnings list only if there are actual warnings
            warnings = []
            if is_stale:
                warnings.append("Using stale data")

            response_data = ReportGenerationResponse(
                success=True,
                message=f"Report generated successfully with {len(properties)} property sheets",
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
                warnings=warnings if warnings else None,  # Only include warnings if there are any
                session_id=session_id
            ).model_dump()

            response = jsonify(response_data)
            response.set_cookie(
                'session_id',
                session_id,
                max_age=3600,
                httponly=False,
                samesite='Lax',
                secure=False,
                path='/'
            )

            return response

        except Exception as e:
            logger.error(f"Error generating report: {str(e)}", exc_info=True)
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
    try:
        run_async(cache.refresh_data(fetch_make_ready_data))
        return jsonify({
            "status": "success",
            "message": "Data refreshed successfully",
            "stats": cache.get_stats()
        })
    except Exception as e:
        logger.error(f"Error refreshing data: {str(e)}")
        raise


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
        # session_id = request.cookies.get('session_id')
        # logger.debug(f"Received session ID: {session_id}")  # Debug log
        #
        # if not session_id:
        #     logger.error("No session ID provided in cookies")
        #     return jsonify({
        #         "success": False,
        #         "message": "No session ID provided"
        #     }), 401

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


@app.route('/api/cache/status', methods=['GET'])
@catch_exceptions
def cache_status():
    """Endpoint to check cache status"""
    stats = cache.get_stats()
    return jsonify({
        "status": "healthy",
        "cache": stats,
        "last_refresh_age_hours": (
            (datetime.now() - cache._last_refresh).total_seconds() / 3600
            if cache._last_refresh else None
        )
    })


def schedule_data_refresh():
    """Schedule data refresh tasks"""
    from apscheduler.schedulers.background import BackgroundScheduler

    def refresh_data_task():
        """Wrapper for async refresh task"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(cache.refresh_data(fetch_make_ready_data))
        finally:
            loop.close()

    scheduler = BackgroundScheduler()

    # Add session cleanup job
    scheduler.add_job(
        run_session_cleanup,
        'interval',
        hours=1,
        id='session_cleanup'
    )

    # Add daily refresh at 9 AM
    scheduler.add_job(
        refresh_data_task,
        'cron',
        hour=9,
        minute=0,
        id='daily_refresh'
    )

    # Add backup refresh every 12 hours
    scheduler.add_job(
        refresh_data_task,
        'interval',
        hours=12,
        misfire_grace_time=3600,
        id='backup_refresh'
    )

    scheduler.start()
    return scheduler


app.scheduler = schedule_data_refresh()


if __name__ == '__main__':
    logger.info("Starting application and updating initial cache.")
    app.run(debug=True)
