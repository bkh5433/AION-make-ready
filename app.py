from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
import shutil
import threading
import asyncio
from flask_cors import CORS
from models.ReportGenerationRequest import ReportGenerationRequest
from models.ReportGenerationResponse import ReportGenerationResponse
from models.ReportOutput import ReportOutput
from datetime import datetime, timedelta, timezone
from typing import List
from pydantic import ValidationError
from property_search import PropertySearch
from logger_config import LogConfig, log_exceptions
from session import get_session_path, cleanup_session, run_session_cleanup, generate_session_id, \
    setup_session_directory
from data_processing import generate_multi_property_report
from cache_module import ConcurrentSQLCache, CacheConfig
from auth_middleware import AuthMiddleware, require_auth, require_role
from config import Config
from queue_manager import queue_manager, queue_requests
from utils.catch_exceptions import catch_exceptions
from monitoring import SystemMonitor
import psutil

app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": Config.CORS_ORIGINS,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "expose_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "max_age": Config.CORS_MAX_AGE
    }
})


# Add CORS headers to all responses
@app.before_request
def before_request():
    """Record the start time of each request"""
    request.start_time = system_monitor.record_request_start()

@app.after_request
def after_request(response):
    """Record the end time and status of each request"""
    if hasattr(request, 'start_time'):
        system_monitor.record_request_end(
            request.start_time,
            error=response.status_code >= 400,
            path=request.path
        )

    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Max-Age', str(Config.CORS_MAX_AGE))

    # Add CORS headers to all responses
    origin = request.headers.get('Origin')
    if origin in Config.CORS_ORIGINS:
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Credentials', 'true')

    return response

# Setup logging
log_config = LogConfig()
logger = log_config.get_logger('api')

# Initialize cache with configuration from Config
cache_config = CacheConfig(**Config.CACHE_CONFIG)
cache = ConcurrentSQLCache(cache_config)

# Initialize authentication middleware
auth = AuthMiddleware()

# Initialize SystemMonitor with other initializations
system_monitor = SystemMonitor()

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
@require_auth
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


@app.route('/api/health')
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    }), 200

@app.route('/api/properties/search', methods=['GET'])
@require_auth
@catch_exceptions
def search_properties():
    """
    Search properties by name.
    Query parameter:
    - q: Search term for property name (optional)
    - include_metrics: Whether to include full metrics (default: true)
    """
    try:
        search_term = request.args.get('q', None)
        include_metrics = request.args.get('include_metrics', 'true').lower() == 'true'

        logger.debug(f"Search parameters - term: {search_term}, include_metrics: {include_metrics}")

        # Get data with confidence score
        data, is_stale, confidence = run_async(cache.get_data())

        if not data:
            logger.info("Cache empty, performing initial population")
            run_async(cache.refresh_data(fetch_make_ready_data))
            data, is_stale, confidence = run_async(cache.get_data())
        elif is_stale and not cache._import_window_detected:
            logger.info("Data is stale and not in import window, triggering background refresh")
            thread = threading.Thread(
                target=run_async,
                args=(cache.refresh_data(fetch_make_ready_data),)
            )
            thread.daemon = True
            thread.start()

        # Initialize searcher
        logger.info("Initializing PropertySearch")
        searcher = PropertySearch(data)

        # Get search results
        logger.info("Executing search")
        result = searcher.get_search_result(
            search_term=search_term,
            last_updated=cache._last_refresh,
            period_info={
                'start_date': datetime.now(timezone.utc) - timedelta(days=30),
                'end_date': datetime.now(timezone.utc)
            }
        )

        logger.info(f"Search complete - found {result.count} properties")

        response_data = {
            'count': result.count,
            'data': [property.model_dump() for property in result.data],
            'is_stale': is_stale,
            'confidence_score': confidence,
            'last_updated': result.last_updated.isoformat() if result.last_updated else None,
            'period_info': {
                'start_date': result.period_info[
                    'start_date'].isoformat() if result.period_info and result.period_info.get('start_date') else None,
                'end_date': result.period_info['end_date'].isoformat() if result.period_info and result.period_info.get(
                    'end_date') else None
            } if result.period_info else None,
            'data_issues': result.data_issues
        }

        if include_metrics:
            response_data['cache_stats'] = {
                'last_refresh': cache._last_refresh.isoformat() if cache._last_refresh else None,
                'is_refreshing': cache._refresh_state.is_refreshing,
                'refresh_age': (
                    (datetime.now(timezone.utc) - cache._last_refresh).total_seconds()
                    if cache._last_refresh else None
                ),
                'import_window_active': cache._import_window_detected,
                'confidence_score': confidence
            }

        logger.info("Returning search results")
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Exception in search_properties", exc_info=True)
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/api/reports/generate', methods=['POST'])
@require_auth
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

        # Get data from cache with confidence score
        data, is_stale, confidence = run_async(cache.get_data())

        if not data:
            logger.info("Cache empty, performing initial population")
            run_async(cache.refresh_data(fetch_make_ready_data))
            data, is_stale, confidence = run_async(cache.get_data())
        elif is_stale and not cache._import_window_detected:
            # Trigger background refresh if data is stale and not in import window
            logger.info("Data is stale and not in import window, triggering background refresh")
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

        # Check for data issues
        if searcher.data_issues:
            logger.warning(f"Found {len(searcher.data_issues)} data issues during report generation")
            warnings = [f"Data quality issues found in {len(searcher.data_issues)} properties"]
        else:
            warnings = []

        if not properties:
            logger.warning(f"No valid properties found for keys: {report_request.properties}")
            return {
                "success": False,
                "message": "No valid properties found matching the request",
                "data_issues": searcher.data_issues  # Include data issues in error response
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
                warnings=warnings if warnings else None,
                data_issues=searcher.data_issues if searcher.data_issues else None,
                session_id=session_id,
                data_quality={
                    'is_stale': is_stale,
                    'confidence_score': confidence,
                    'import_window_active': cache._import_window_detected
                }
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
@require_auth
@require_role('admin')
@catch_exceptions
@log_exceptions(logger)
def refresh_data():
    logger.info("POST /api/refresh endpoint accessed. Force refreshing data.")
    try:
        # Start refresh in background thread to not block the response
        def refresh_background():
            try:
                run_async(cache.refresh_data(fetch_make_ready_data))
                logger.info("Background refresh completed successfully")
            except Exception as e:
                logger.error(f"Background refresh failed: {str(e)}")

        thread = threading.Thread(target=refresh_background)
        thread.daemon = True
        thread.start()

        # Return immediately with success status
        return jsonify({
            "status": "success",
            "message": "Data refresh initiated",
            "stats": cache.get_stats()
        })
    except Exception as e:
        logger.error(f"Error initiating refresh: {str(e)}")
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

@app.route('/api/reports/download', methods=['GET'])
@require_auth
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
@require_auth
@catch_exceptions
def cache_status():
    """Enhanced endpoint to check cache status and update patterns"""
    try:
        stats = cache.get_stats()
        now = datetime.now(timezone.utc)

        # Calculate time until next expected update
        expected_time = datetime.strptime(cache.config.expected_update_time, "%H:%M").time()
        expected_datetime = datetime.combine(now.date(), expected_time, tzinfo=timezone.utc)

        if now.time() > expected_time:
            # If we're past today's update time, look at tomorrow
            expected_datetime = datetime.combine(now.date() + timedelta(days=1), expected_time, tzinfo=timezone.utc)

        time_until_update = (expected_datetime - now).total_seconds()

        # Calculate next check datetime
        next_check_datetime = now + timedelta(seconds=cache._next_check_interval)
        expected_update_datetime = expected_datetime

        # Enhanced status response
        response = {
            "status": "healthy",
            "cache": stats,
            "update_info": {
                "last_refresh": cache._last_refresh.isoformat() if cache._last_refresh else None,
                "last_data_change": cache._last_data_change.isoformat() if cache._last_data_change else None,
                "last_refresh_age_hours": (
                    (now - cache._last_refresh).total_seconds() / 3600
                    if cache._last_refresh else None
                ),
                "next_check_interval_seconds": cache._next_check_interval,
                "next_check_datetime": next_check_datetime.isoformat(),
                "expected_update_time": cache.config.expected_update_time,
                "expected_update_datetime": expected_update_datetime.isoformat(),
                "time_until_update_seconds": time_until_update,
                "time_until_update_hours": time_until_update / 3600,
                "is_update_window": (
                        abs(time_until_update) <= cache.config.update_window
                ),
                "import_window_detected": cache._import_window_detected
            },
            "version_info": {
                "current_version": cache._current_version,
                "primary_record_count": len(cache._primary_cache.data) if cache._primary_cache else 0,
                "fallback_record_count": len(cache._fallback_cache.data) if cache._fallback_cache else 0,
                "confidence_score": cache._calculate_confidence_score(
                    cache._primary_cache) if cache._primary_cache else 0.0
            },
            "refresh_state": {
                "is_refreshing": cache._refresh_state.is_refreshing,
                "refresh_started": (
                    cache._refresh_state.refresh_started.isoformat()
                    if cache._refresh_state.refresh_started else None
                ),
                "refresh_completed": (
                    cache._refresh_state.refresh_completed.isoformat()
                    if cache._refresh_state.refresh_completed else None
                ),
                "current_waiters": cache._refresh_state.waiters,
                "last_error": cache._refresh_state.error
            },
            "performance_metrics": {
                "access_count": stats["performance"]["access_count"],
                "refresh_count": stats["performance"]["refresh_count"],
                "failed_refreshes": stats["performance"]["failed_refreshes"],
                "stale_data_served_count": stats["performance"]["stale_data_served_count"],
                "avg_refresh_time": stats["performance"].get("avg_refresh_time"),
                "avg_wait_time": stats["performance"].get("avg_wait_time")
            },
            "configuration": {
                "base_refresh_interval": cache.config.base_refresh_interval,
                "max_refresh_interval": cache.config.max_refresh_interval,
                "force_refresh_interval": cache.config.force_refresh_interval,
                "update_window_seconds": cache.config.update_window,
                "stale_if_error": cache.config.stale_if_error,
                "max_retry_attempts": cache.config.max_retry_attempts
            }
        }

        # Add warning flags
        warnings = []
        if cache.is_stale:
            warnings.append("Cache is stale")
        if cache.needs_force_refresh:
            warnings.append("Cache needs force refresh")
        if cache._refresh_state.error:
            warnings.append(f"Last refresh error: {cache._refresh_state.error}")
        if cache._import_window_detected:
            warnings.append("Import window detected - using fallback data")
        if not cache._primary_cache:
            warnings.append("No primary cache data available")

        if warnings:
            response["warnings"] = warnings

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error getting cache status: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Error retrieving cache status",
            "error": str(e)
        }), 500

def schedule_data_refresh():
    """Enhanced dynamic scheduling for data refresh"""
    from apscheduler.schedulers.background import BackgroundScheduler

    async def calculate_interval():
        """Get the next check interval from cache"""
        interval = cache._calculate_next_check_interval()
        logger.info(f"Calculated next check interval: {interval} seconds")
        return interval
    
    def refresh_data_task():
        """Wrapper for async refresh task"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # First refresh the data
            loop.run_until_complete(cache.refresh_data(fetch_make_ready_data))

            # Then calculate new interval
            next_interval = loop.run_until_complete(calculate_interval())

            # Update scheduler with new interval
            logger.info(f"Rescheduling next refresh for {next_interval} seconds")
            scheduler.reschedule_job(
                'dynamic_refresh',
                trigger='interval',
                seconds=next_interval
            )

        except Exception as e:
            logger.error(f"Error in refresh task: {str(e)}")
        finally:
            loop.close()

    scheduler = BackgroundScheduler()

    # Start with initial interval from cache
    initial_interval = run_async(calculate_interval())
    
    scheduler.add_job(
        refresh_data_task,
        'interval',
        seconds=initial_interval,
        id='dynamic_refresh'
    )

    scheduler.start()
    return scheduler

app.scheduler = schedule_data_refresh()

@app.route('/api/auth/login', methods=['POST'])
@catch_exceptions
def login():
    """Login endpoint"""
    try:
        data = request.get_json()
        logger.debug(f"Login attempt with data: {data}")  # Add debug logging

        if not data:
            logger.warning("Login attempt with no data")
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400

        username = data.get('username')
        password = data.get('password')

        logger.debug(f"Login attempt for username: {username}")  # Add debug logging

        if not username or not password:
            logger.warning(
                f"Login attempt missing credentials - username: {bool(username)}, password: {bool(password)}")
            return jsonify({
                'success': False,
                'message': 'Username and password required'
            }), 400

        result = auth.authenticate(username, password)
        if result:
            logger.info(f"Successful login for user: {username}")  # Add success logging
            return jsonify({
                'success': True,
                'message': 'Login successful',
                **result
            }), 200

        logger.warning(f"Failed login attempt for user: {username}")  # Add failure logging
        return jsonify({
            'success': False,
            'message': 'Invalid credentials'
        }), 401

    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'An error occurred during login'
        }), 500

@app.route('/api/auth/register', methods=['POST'])
@require_auth
@require_role('admin')
@catch_exceptions
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400

        username = data.get('username')
        password = data.get('password')
        name = data.get('name')
        role = data.get('role', 'user')  # Default to 'user' if not specified

        if not all([username, password, name]):
            return jsonify({
                'success': False,
                'message': 'Username, password, and name are required'
            }), 400

        if role not in ['user', 'admin']:
            return jsonify({
                'success': False,
                'message': 'Invalid role'
            }), 400

        user_data = auth.create_user(username, password, name, role)

        return jsonify({
            'success': True,
            'message': 'User created successfully',
            'user': user_data
        }), 201

    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred during registration'
        }), 500

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user():
    """Get current user information"""
    return jsonify({
        'user': request.user
    })

@app.route('/api/users', methods=['GET'])
@require_auth
@require_role('admin')
def list_users():
    """List all users (admin only)"""
    try:
        users = auth.users_ref.stream()
        user_list = [{
            'email': user.get('email'),
            'name': user.get('name'),
            'role': user.get('role'),
            'lastLogin': user.get('lastLogin'),
            'isActive': user.get('isActive')
        } for user in (doc.to_dict() for doc in users)]

        return jsonify({
            'users': user_list
        })
    except Exception as e:
        return jsonify({
            'message': f'Error fetching users: {str(e)}'
        }), 500

@app.route('/api/users/<email>/role', methods=['PUT'])
@require_auth
@require_role('admin')
def update_user_role(email):
    """Update user role (admin only)"""
    data = request.get_json()
    new_role = data.get('role')

    if not new_role:
        return jsonify({
            'message': 'Role is required'
        }), 400

    if new_role not in ['user', 'admin']:
        return jsonify({
            'message': 'Invalid role'
        }), 400

    success = auth.update_user_role(email, new_role)
    if success:
        return jsonify({
            'message': f'Role updated for {email}'
        })

    return jsonify({
        'message': 'User not found'
    }), 404

@app.route('/api/admin/users', methods=['GET'])
@require_auth
@require_role('admin')
def get_users():
    """Get all users"""
    try:
        users = auth.users_ref.stream()
        user_list = [{
            'email': user.get('email'),
            'name': user.get('name'),
            'username': user.get('username'),
            'role': user.get('role'),
            'lastLogin': user.get('lastLogin'),
            'isActive': user.get('isActive'),
            'createdAt': user.get('createdAt'),
            'uid': doc.id  # Include the document ID as uid
        } for doc, user in ((doc, doc.to_dict()) for doc in users)]

        return jsonify({
            'success': True,
            'users': user_list
        })
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error fetching users'
        }), 500


@app.route('/api/admin/users/<user_id>', methods=['PUT', 'DELETE'])
@require_auth
@require_role('admin')
def manage_user(user_id):
    """Update or delete user details"""
    try:
        # Get user document
        user_doc = auth.users_ref.document(user_id).get()
        if not user_doc.exists:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404

        if request.method == 'DELETE':
            # Delete the user
            user_doc.reference.delete()
            return jsonify({
                'success': True,
                'message': 'User deleted successfully'
            })

        elif request.method == 'PUT':
            data = request.get_json()

            # Don't allow role change to admin for non-admin users
            if data.get('role') == 'admin' and request.user['role'] != 'admin':
                return jsonify({
                    'success': False,
                    'message': 'Unauthorized to assign admin role'
                }), 403

            updates = {
                'name': data.get('name'),
                'role': data.get('role'),
                'isActive': data.get('isActive', True)
            }

            # Remove None values
            updates = {k: v for k, v in updates.items() if v is not None}

            if data.get('password'):
                password_hash, salt = auth._hash_password(data['password'])
                updates['password_hash'] = password_hash
                updates['salt'] = salt

            user_doc.reference.update(updates)

            return jsonify({
                'success': True,
                'message': 'User updated successfully'
            })
    except Exception as e:
        logger.error(f"Error managing user: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error managing user: {str(e)}'
        }), 500

@app.route('/api/admin/logs', methods=['GET'])
@require_auth
@require_role(['admin'])
def get_activity_logs():
    """Get activity logs with optional filtering"""
    try:
        level = request.args.get('level', 'all')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = int(request.args.get('limit', 100))

        logs = log_config.get_recent_logs(
            level=level,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        return jsonify({
            'status': 'success',
            'logs': logs
        })
    except Exception as e:
        logger.error(f"Error retrieving logs: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/system/metrics', methods=['GET'])
@require_auth
@require_role('admin')
@catch_exceptions
@log_exceptions(logger)
def get_system_metrics():
    """Get system metrics for monitoring"""
    try:
        metrics = system_monitor.get_all_metrics()
        return jsonify({
            "success": True,
            "metrics": metrics
        })
    except Exception as e:
        logger.error(f"Error getting system metrics: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Error retrieving system metrics",
            "error": str(e)
        }), 500


@app.route('/api/admin/users/<user_id>/status', methods=['PUT', 'OPTIONS'])
@require_auth
@require_role('admin')
def update_user_status(user_id):
    """Update user active status"""
    try:
        if request.method == 'OPTIONS':
            return '', 204

        data = request.get_json()
        is_active = data.get('isActive')

        if is_active is None:
            return jsonify({
                'success': False,
                'message': 'isActive status is required'
            }), 400

        # Get user document directly by ID
        user_doc = auth.users_ref.document(user_id).get()

        if not user_doc.exists:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404

        # Update the user's status
        user_doc.reference.update({
            'isActive': is_active
        })

        return jsonify({
            'success': True,
            'message': 'User status updated successfully'
        })
    except Exception as e:
        logger.error(f"Error updating user status: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error updating user status'
        }), 500


@app.route('/api/auth/change-password', methods=['POST'])
@require_auth
def change_password():
    """Change user password"""
    try:
        data = request.get_json()
        current_password = data.get('currentPassword')
        new_password = data.get('newPassword')

        if not current_password or not new_password:
            return jsonify({
                'success': False,
                'message': 'Current and new passwords are required'
            }), 400

        # Get user from Firestore
        user_doc = auth.users_ref.where('email', '==', request.user['email']).limit(1).stream()
        user = next((doc.to_dict() for doc in user_doc), None)

        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404

        # Verify current password
        hashed_input, _ = auth._hash_password(current_password, user['salt'])
        if hashed_input != user['password_hash']:
            return jsonify({
                'success': False,
                'message': 'Current password is incorrect'
            }), 400

        # Update password
        new_hash, new_salt = auth._hash_password(new_password)
        user_ref = auth.users_ref.document(user['uid'])
        user_ref.update({
            'password_hash': new_hash,
            'salt': new_salt,
            'requirePasswordChange': False
        })

        return jsonify({
            'success': True,
            'message': 'Password updated successfully'
        })

    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while changing password'
        }), 500


@app.route('/api/admin/system/status', methods=['GET'])
@require_auth
@require_role('admin')
@catch_exceptions
def system_status():
    """Get comprehensive system status"""
    try:
        # Get system metrics
        metrics = system_monitor.get_all_metrics()

        # Get users who logged in within the last 12 hours
        twelve_hours_ago = datetime.utcnow() - timedelta(hours=12)
        active_users = 0

        # Query Firestore for recent logins
        users = auth.users_ref.where('lastLogin', '>=', twelve_hours_ago.strftime('%Y-%m-%dT%H:%M:%S.%fZ')).stream()
        active_users = len(list(users))

        # Get cache health
        cache_healthy = cache.is_healthy() if hasattr(cache, 'is_healthy') else True
        cache_stats = cache.get_stats()

        # Get current data stats
        current_data_count = len(cache._primary_cache.data) if cache._primary_cache else 0
        fallback_data_count = len(cache._fallback_cache.data) if cache._fallback_cache else 0

        response = {
            'healthy': cache_healthy,  # Overall health based on cache and system metrics
            'timestamp': datetime.now().isoformat(),
            'activeUsers': active_users,  # Now shows users active in last 12 hours
            'cpu': metrics['cpu'],
            'memory': metrics['memory'],
            'disk': metrics['disk'],
            'network': metrics['network'],
            'performance': metrics['performance'],
            'cache': {
                **cache_stats,
                'current_data_count': current_data_count,
                'fallback_data_count': fallback_data_count,
                'import_window_active': cache._import_window_detected if hasattr(cache,
                                                                                 '_import_window_detected') else False,
                'confidence_score': cache._calculate_confidence_score(
                    cache._primary_cache) if cache._primary_cache else 0.0
            }
        }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        return jsonify({
            'healthy': False,
            'error': str(e),
            'details': 'Error retrieving system status'
        }), 500


@app.route('/api/import-window/status', methods=['GET'])
@require_auth
@catch_exceptions
def import_window_status():
    """Get the current import window status"""
    try:
        now = datetime.now(timezone.utc)
        status = {
            'in_import_window': cache._import_window_detected,
            'last_import_window': cache._last_import_window.isoformat() if cache._last_import_window else None,
            'consecutive_null_count': cache._consecutive_null_count,
            'timestamp': now.isoformat(),
            'cache_status': {
                'is_refreshing': cache._refresh_state.is_refreshing,
                'last_refresh': cache._last_refresh.isoformat() if cache._last_refresh else None,
                'next_check_interval': cache._next_check_interval
            }
        }
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting import window status: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500


@app.route('/api/test/trigger-import-window', methods=['POST'])
@require_auth
# @require_role('admin')  # Only allow admins to trigger this
@catch_exceptions
def trigger_import_window():
    """Test endpoint to manually trigger import window state"""
    try:
        action = request.json.get('action', 'start')
        logger.info(f"Triggering import window action: {action}")

        if action == 'start':
            # Force the import window state
            cache._consecutive_null_count = 2
            cache._import_window_detected = True
            cache._last_import_window = datetime.now(timezone.utc)
            message = "Import window started"
        elif action == 'end':
            # Reset the import window state
            cache._consecutive_null_count = 0
            cache._import_window_detected = False
            cache._last_import_window = datetime.now(timezone.utc)
            message = "Import window ended"
        else:
            raise ValueError(f"Invalid action: {action}")

        logger.info(f"Import window status changed - Message: {message}, Active: {cache._import_window_detected}")
        return jsonify({
            'status': 'success',
            'message': message,
            'import_window_active': cache._import_window_detected,
            'last_import_window': cache._last_import_window.isoformat() if cache._last_import_window else None
        })

    except Exception as e:
        logger.error(f"Error triggering import window: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

if __name__ == '__main__':
    logger.info("Starting application and updating initial cache.")
    app.run(debug=True)

# @app.route('/api/some_endpoint', methods=['GET'])
# @require_auth
# @catch_exceptions
# @log_exceptions(logger)
# def some_endpoint():
#     # Construct dynamic URL using Config
#     dynamic_url = f"http://{Config.API_HOST}:{Config.API_PORT}/api/some_other_endpoint"

#     # Use dynamic_url as needed
#     response = {
#         "message": "This is a dynamically constructed URL.",
#         "url": dynamic_url
#     }
#     return jsonify(response), 200
