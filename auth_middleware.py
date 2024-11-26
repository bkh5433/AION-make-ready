from functools import wraps
from flask import request, jsonify
from datetime import datetime, timedelta
import jwt
import os
from typing import Optional
import firebase_admin
from firebase_admin import credentials, firestore
import hashlib
import secrets

from logger_config import LogConfig
from utils.path_resolver import PathResolver

# Initialize Firebase
cred = credentials.Certificate(PathResolver.resolve_template_path('firebase-admin.json'))
firebase_admin.initialize_app(cred)
db = firestore.client()

SECRET_KEY = os.getenv('JWT_SECRET_KEY', secrets.token_hex(32))

logger_config = LogConfig()
logger = logger_config.get_logger("auth_middleware")


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
            'user_id': user_data['uid'],
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

    def authenticate(self, username: str, password: str) -> Optional[dict]:
        """Authenticate user with username/password"""
        try:
            # Query Firestore for user
            users = self.users_ref.where('username', '==', username).limit(1).stream()
            user = next((user.to_dict() for user in users), None)

            if not user:
                logger.warning(f"User not found: {username}")
                return None

            # Verify password
            hashed_input, _ = self._hash_password(password, user['salt'])
            if hashed_input != user['password_hash']:
                logger.info(f"Password mismatch for user: {username}")
                return None

            # Update last login
            user_ref = self.users_ref.document(user['uid'])
            user_ref.update({
                'lastLogin': datetime.now(datetime.UTC).isoformat()
            })

            # Calculate token expiration time
            expiration_time = datetime.utcnow() + timedelta(hours=24)

            # Generate token with complete user data
            token = self.generate_token({
                'uid': user['uid'],
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
                    'email': user['email']
                },
                'expires_at': expiration_time.isoformat(),  # Add expiration time to response
                'expires_in': int(timedelta(hours=24).total_seconds())  # Add seconds until expiration
            }
        except Exception as e:
            logger.warning(f"Authentication error: {e}, username: {username}")
            return None

    def create_user(self, username: str, password: str, name: str, role: str = 'user') -> dict:
        """Create a new user with role"""
        try:
            # Check if user already exists
            existing_users = self.users_ref.where('username', '==', username).limit(1).stream()
            if next((user for user in existing_users), None):
                raise ValueError("User with this username already exists")

            # Hash password
            password_hash, salt = self._hash_password(password)

            # Create new user document
            user_data = {
                'uid': self.users_ref.document().id,
                'username': username,
                'email': username,  # Using username as email for now
                'password_hash': password_hash,
                'salt': salt,
                'name': name,
                'isActive': True,
                'createdAt': datetime.now(datetime.UTC).isoformat(),
                'lastLogin': None,
                'role': role  # Add role to user data
            }

            self.users_ref.document(user_data['uid']).set(user_data)

            # Return a sanitized version without sensitive data
            return {
                'username': user_data['username'],
                'name': user_data['name'],
                'role': user_data['role']
            }
        except Exception as e:
            logger.warning(f"Error creating user: {e}")
            raise

    def get_user_role(self, email: str) -> Optional[str]:
        """Get user's role"""
        try:
            users = self.users_ref.where('email', '==', email).limit(1).stream()
            user = next((user.to_dict() for user in users), None)
            return user.get('role') if user else None
        except Exception as e:
            print(f"Error getting user role: {e}")
            return None

    def update_user_role(self, email: str, new_role: str) -> bool:
        """Update user's role (admin only)"""
        try:
            users = self.users_ref.where('email', '==', email).limit(1).stream()
            user_doc = next((doc for doc in users), None)

            if user_doc:
                user_doc.reference.update({'role': new_role})
                return True
            return False
        except Exception as e:
            print(f"Error updating user role: {e}")
            return False


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
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'message': 'Invalid token format'}), 401

    return decorated


def require_role(required_role):
    """Decorator to require specific role for routes"""

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Get user from the @require_auth decorator
            user = request.user

            # Query Firestore for user's role
            try:
                auth = AuthMiddleware()
                user_doc = auth.users_ref.where('email', '==', user['email']).limit(1).stream()
                user_data = next((doc.to_dict() for doc in user_doc), None)

                if not user_data:
                    return jsonify({'message': 'User not found'}), 404

                user_role = user_data.get('role', 'user')

                # Check if user has required role
                if required_role == 'admin' and user_role != 'admin':
                    return jsonify({'message': 'Admin access required'}), 403

                return f(*args, **kwargs)
            except Exception as e:
                print(f"Role verification error: {e}")
                return jsonify({'message': 'Error verifying user role'}), 500

        return decorated

    return decorator
