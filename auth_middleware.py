from functools import wraps
from flask import request, jsonify
from datetime import datetime, timedelta
import jwt
from typing import Optional
import firebase_admin
from firebase_admin import credentials, firestore
import hashlib
import secrets
import asyncio
from logger_config import LogConfig
from config import Config

# Initialize Firebase
cred = credentials.Certificate({
    "type": "service_account",
    "project_id": Config.FIREBASE_CONFIG['project_id'],
    "private_key_id": Config.FIREBASE_CONFIG['private_key_id'],
    "private_key": Config.FIREBASE_CONFIG['private_key'].replace('\\n', '\n') if Config.FIREBASE_CONFIG[
        'private_key'] else '',
    "client_email": Config.FIREBASE_CONFIG['client_email'],
    "client_id": Config.FIREBASE_CONFIG['client_id'],
    "auth_uri": Config.FIREBASE_CONFIG['auth_uri'],
    "token_uri": Config.FIREBASE_CONFIG['token_uri'],
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{Config.FIREBASE_CONFIG['client_email']}"
})
firebase_admin.initialize_app(cred)
db = firestore.client()

SECRET_KEY = Config.JWT_SECRET_KEY

logger_config = LogConfig()
logger = logger_config.get_logger("auth_middleware")


def run_async(coro):
    """Helper function to run async code in sync context"""
    if not asyncio.iscoroutine(coro):
        return coro
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        should_close = True
    else:
        should_close = False

    try:
        result = loop.run_until_complete(coro)
        return result
    finally:
        if should_close:
            loop.close()


def wrap_async(f):
    """Decorator to wrap async functions for sync contexts"""

    @wraps(f)
    def wrapped(*args, **kwargs):
        return run_async(f(*args, **kwargs))

    return wrapped


# Remote Info Management
@wrap_async
async def get_remote_info():
    try:
        doc_ref = db.collection('system').document('remote_info')
        doc = await asyncio.get_event_loop().run_in_executor(None, doc_ref.get)
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        logger.error(f"Error getting remote info: {e}")
        return None


def get_remote_info_sync():
    """Synchronous wrapper for get_remote_info"""
    return run_async(get_remote_info())


@wrap_async
async def set_remote_info(message, status='info'):
    try:
        doc_ref = db.collection('system').document('remote_info')
        await asyncio.get_event_loop().run_in_executor(
            None,
            doc_ref.set,
            {
                'message': message,
                'status': status,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
        )
        return True
    except Exception as e:
        logger.error(f"Error setting remote info: {e}")
        return False


def set_remote_info_sync(message, status='info'):
    """Synchronous wrapper for set_remote_info"""
    return run_async(set_remote_info(message, status))


@wrap_async
async def clear_remote_info():
    try:
        doc_ref = db.collection('system').document('remote_info')
        await asyncio.get_event_loop().run_in_executor(None, doc_ref.delete)
        return True
    except Exception as e:
        logger.error(f"Error clearing remote info: {e}")
        return False


def clear_remote_info_sync():
    """Synchronous wrapper for clear_remote_info"""
    return run_async(clear_remote_info())

class AuthMiddleware:
    def __init__(self):
        self.users_ref = db.collection('users')

    def _hash_password(self, password: str, salt: str = None) -> tuple[str, str]:
        """Hash password with salt"""
        if not salt:
            salt = secrets.token_hex(16)
        hash_obj = hashlib.sha256((password + salt).encode())
        return hash_obj.hexdigest(), salt

    def generate_token(self, user_data: dict) -> str:
        """Generate a JWT token for the user"""
        payload = {
            'user_id': user_data['user_id'],
            'username': user_data['username'],
            'email': user_data['email'],
            'name': user_data['name'],
            'role': user_data['role'],
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

    def verify_token(self, token: str) -> Optional[dict]:
        """Verify JWT token and return payload if valid"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            return payload
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None

    async def authenticate(self, username: str, password: str) -> Optional[dict]:
        """Authenticate user with username/password"""
        try:
            # Query Firestore for user
            query = self.users_ref.where('username', '==', username).limit(1)
            users = await asyncio.get_event_loop().run_in_executor(None, query.stream)
            user = next((user.to_dict() for user in users), None)

            if not user:
                logger.warning(f"User not found: {username}")
                return None

            # Verify password
            hashed_input, _ = self._hash_password(password, user['salt'])
            if hashed_input != user['password_hash']:
                logger.info(f"Password mismatch for user: {username}")
                return None

            # Update last login with UTC timezone
            user_ref = self.users_ref.document(user.get('user_id', user.get('uid')))
            await asyncio.get_event_loop().run_in_executor(
                None,
                user_ref.update,
                {'lastLogin': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')}
            )

            # Calculate token expiration time
            expiration_time = datetime.utcnow() + timedelta(hours=24)

            # Generate token with complete user data
            token = self.generate_token({
                'user_id': user.get('user_id', user.get('uid')),
                'username': user['username'],
                'email': user['email'],
                'name': user['name'],
                'role': user['role']
            })

            return {
                'token': token,
                'user': {
                    'username': user['username'],
                    'name': user['name'],
                    'role': user['role'],
                    'email': user['email'],
                    'requirePasswordChange': user.get('requirePasswordChange', False)
                },
                'expires_at': expiration_time.isoformat(),
                'expires_in': int(timedelta(hours=24).total_seconds())
            }
        except Exception as e:
            logger.warning(f"Authentication error: {e}, username: {username}")
            return None

    def authenticate_sync(self, username: str, password: str) -> Optional[dict]:
        """Synchronous wrapper for authenticate"""
        return run_async(self.authenticate(username, password))

    async def create_user(self, username: str, password: str, name: str, role: str = 'user') -> dict:
        """Create a new user with role"""
        try:
            # Check if user already exists
            query = self.users_ref.where('username', '==', username).limit(1)
            existing_users = await asyncio.get_event_loop().run_in_executor(None, query.stream)
            if next((user for user in existing_users), None):
                raise ValueError("User with this username already exists")

            # Hash password
            password_hash, salt = self._hash_password(password)

            # Get current UTC time
            now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

            # Create new user document
            user_data = {
                'user_id': self.users_ref.document().id,
                'username': username,
                'email': username,
                'password_hash': password_hash,
                'salt': salt,
                'name': name,
                'isActive': True,
                'createdAt': now,
                'lastLogin': None,
                'role': role
            }

            await asyncio.get_event_loop().run_in_executor(
                None,
                self.users_ref.document(user_data['user_id']).set,
                user_data
            )

            # Return a sanitized version without sensitive data
            return {
                'username': user_data['username'],
                'name': user_data['name'],
                'role': user_data['role'],
                'createdAt': now
            }
        except Exception as e:
            logger.warning(f"Error creating user: {e}")
            raise

    def create_user_sync(self, username: str, password: str, name: str, role: str = 'user') -> dict:
        """Synchronous wrapper for create_user"""
        return run_async(self.create_user(username, password, name, role))

    async def get_user_role(self, email: str) -> Optional[str]:
        """Get user's role"""
        try:
            query = self.users_ref.where('email', '==', email).limit(1)
            users = await asyncio.get_event_loop().run_in_executor(None, query.stream)
            user = next((user.to_dict() for user in users), None)
            return user.get('role') if user else None
        except Exception as e:
            logger.error(f"Error getting user role: {e}")
            return None

    def get_user_role_sync(self, email: str) -> Optional[str]:
        """Synchronous wrapper for get_user_role"""
        return run_async(self.get_user_role(email))

    async def update_user_role(self, email: str, new_role: str) -> bool:
        """Update user's role (admin only)"""
        try:
            query = self.users_ref.where('email', '==', email).limit(1)
            users = await asyncio.get_event_loop().run_in_executor(None, query.stream)
            user_doc = next((doc for doc in users), None)

            if user_doc:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    user_doc.reference.update,
                    {'role': new_role}
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating user role: {e}")
            return False

    def update_user_role_sync(self, email: str, new_role: str) -> bool:
        """Synchronous wrapper for update_user_role"""
        return run_async(self.update_user_role(email, new_role))

def require_auth(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({'message': 'Missing authorization header'}), 401

        try:
            token = auth_header.split(' ')[1]
            auth = AuthMiddleware()
            payload = auth.verify_token(token)

            if not payload:
                return jsonify({'message': 'Invalid or expired token'}), 401

            request.user = payload

            if asyncio.iscoroutinefunction(f):
                return wrap_async(f)(*args, **kwargs)
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Auth error: {str(e)}")
            return jsonify({'message': 'Invalid token format'}), 401

    return decorated

def require_role(required_role):
    """Decorator to require specific role for routes"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = request.user

            try:
                auth = AuthMiddleware()
                user_role = auth.get_user_role_sync(user['email'])

                if not user_role:
                    return jsonify({'message': 'User not found'}), 404

                if required_role == 'admin' and user_role != 'admin':
                    return jsonify({'message': 'Admin access required'}), 403

                if asyncio.iscoroutinefunction(f):
                    return wrap_async(f)(*args, **kwargs)
                return f(*args, **kwargs)
            except Exception as e:
                logger.error(f"Role verification error: {e}")
                return jsonify({'message': 'Error verifying user role'}), 500

        return decorated
    return decorator


# Export sync functions
__all__ = [
    'get_remote_info', 'get_remote_info_sync',
    'set_remote_info', 'set_remote_info_sync',
    'clear_remote_info', 'clear_remote_info_sync',
    'AuthMiddleware', 'require_auth', 'require_role',
    'db'
]
