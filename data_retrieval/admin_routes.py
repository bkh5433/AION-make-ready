from flask import Blueprint, jsonify, request, current_app
import psutil
import datetime
from functools import wraps
import os
from logger_config import log_exceptions
from auth_middleware import AuthMiddleware, require_auth, require_role

admin_bp = Blueprint('admin', __name__)

# Initialize auth middleware
auth = AuthMiddleware()


def verify_admin_token(token):
    # TODO: Implement proper token verification
    return token == "admin-token-123"  # Temporary simple verification


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not verify_admin_token(auth_header):
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Admin access required'
            }), 401
        return f(*args, **kwargs)

    return decorated_function


@admin_bp.route('/api/admin/system-stats')
@admin_required
def get_system_stats():
    try:
        cpu_load = psutil.cpu_percent()
        memory = psutil.virtual_memory()

        # Get process info
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info().rss / 1024 / 1024  # Convert to MB

        return jsonify({
            'apiHealth': 'healthy',
            'cacheStatus': 'active',
            'memoryUsage': {
                'system': memory.percent,
                'application': round(process_memory, 2)
            },
            'cpuLoad': cpu_load,
            'uptime': get_uptime(),
            'processInfo': {
                'pid': process.pid,
                'threads': process.num_threads(),
                'created': datetime.datetime.fromtimestamp(process.create_time()).isoformat()
            }
        })
    except Exception as e:
        current_app.logger.error(f"Error getting system stats: {str(e)}")
        return jsonify({
            'error': 'Failed to get system statistics',
            'message': str(e)
        }), 500


@admin_bp.route('/api/admin/logs')
@admin_required
def get_logs():
    try:
        # Get the last 100 log entries
        log_file = 'app.log'  # Default log file path
        logs = []

        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                lines = f.readlines()[-100:]
                for line in lines:
                    try:
                        parts = line.split(' - ')
                        timestamp = parts[0]
                        level = parts[1]
                        message = ' - '.join(parts[2:]).strip()

                        logs.append({
                            'timestamp': timestamp,
                            'level': level.lower(),
                            'message': message
                        })
                    except Exception as e:
                        current_app.logger.error(f"Error parsing log line: {str(e)}")
                        continue

        return jsonify(logs)
    except Exception as e:
        return jsonify({
            'error': 'Failed to get logs',
            'message': str(e)
        }), 500


@admin_bp.route('/api/admin/refresh-cache', methods=['POST'])
@admin_required
def refresh_cache():
    try:
        # Access cache through current_app
        if hasattr(current_app, 'cache'):
            current_app.cache.clear()
            return jsonify({
                'status': 'success',
                'message': 'Cache refreshed successfully',
                'timestamp': datetime.datetime.now().isoformat()
            })
        else:
            return jsonify({
                'error': 'Cache not initialized',
                'message': 'Application cache is not available'
            }), 500
    except Exception as e:
        return jsonify({
            'error': 'Failed to refresh cache',
            'message': str(e)
        }), 500


@admin_bp.route('/api/users', methods=['GET'])
@require_auth
@require_role('admin')
def list_users():
    try:
        # Get all users from Firestore
        users = []
        for user_doc in auth.users_ref.stream():
            user_data = user_doc.to_dict()
            # Include uid in the response
            users.append({
                'uid': user_data.get('uid'),
                'username': user_data.get('username'),
                'email': user_data.get('email'),
                'name': user_data.get('name'),
                'role': user_data.get('role', 'user'),
                'isActive': user_data.get('isActive', True),
                'createdAt': user_data.get('createdAt'),
                'lastLogin': user_data.get('lastLogin')
            })

        return jsonify({
            'success': True,
            'users': users
        })
    except Exception as e:
        current_app.logger.error(f"Error listing users: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to list users',
            'message': str(e)
        }), 500


@admin_bp.route('/api/users/<uid>', methods=['PUT'])
@require_auth
@require_role('admin')
def update_user(uid):
    try:
        data = request.get_json()

        # Get user document
        user_ref = auth.users_ref.document(uid)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        # Update allowed fields
        update_data = {}
        if 'name' in data:
            update_data['name'] = data['name']
        if 'role' in data:
            update_data['role'] = data['role']
        if 'isActive' in data:
            update_data['isActive'] = data['isActive']

        user_ref.update(update_data)

        return jsonify({
            'success': True,
            'message': 'User updated successfully'
        })
    except Exception as e:
        current_app.logger.error(f"Error updating user: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to update user',
            'message': str(e)
        }), 500


@admin_bp.route('/api/users/<uid>', methods=['DELETE'])
@require_auth
@require_role('admin')
def delete_user(uid):
    try:
        # Get user document
        user_ref = auth.users_ref.document(uid)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        # Delete the user
        user_ref.delete()

        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        })
    except Exception as e:
        current_app.logger.error(f"Error deleting user: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete user',
            'message': str(e)
        }), 500


@admin_bp.route('/api/users/<uid>/reset-password', methods=['POST'])
@require_auth
@require_role('admin')
def reset_user_password(uid):
    try:
        # Get user document
        user_ref = auth.users_ref.document(uid)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404

        # Reset password to 'aion' and require change
        password_hash, salt = auth._hash_password('aion')
        user_ref.update({
            'password_hash': password_hash,
            'salt': salt,
            'requirePasswordChange': True
        })

        return jsonify({
            'success': True,
            'message': 'Password reset successfully'
        })
    except Exception as e:
        current_app.logger.error(f"Error resetting password: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to reset password',
            'message': str(e)
        }), 500


def get_uptime():
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])

        days = int(uptime_seconds // (24 * 3600))
        hours = int((uptime_seconds % (24 * 3600)) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)

        return f"{days}d {hours}h {minutes}m"
    except:
        # Fallback for non-Linux systems
        return "Unknown"
