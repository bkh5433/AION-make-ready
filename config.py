from decouple import config
from datetime import timedelta
import os

class Config:
    # Database
    DB_SERVER = config('DB_SERVER')
    DB_NAME = config('DB_NAME')
    DB_USER = config('DB_USER')
    DB_PASSWORD = config('DB_PASSWORD')

    # API
    API_HOST = config('API_HOST', default='0.0.0.0')
    API_PORT = config('API_PORT', default=5000, cast=int)
    API_DEBUG = config('API_DEBUG', default=False, cast=bool)

    # CORS
    CORS_ORIGINS = [origin.strip() for origin in
                    config('CORS_ORIGINS', default="http://localhost:5173,http://127.0.0.1:5173").split(',')]
    CORS_MAX_AGE = config('CORS_MAX_AGE', default=3600, cast=int)

    # Cache
    CACHE_CONFIG = {
        'force_refresh_interval': config('CACHE_FORCE_REFRESH', default=43200, cast=int),
        'refresh_timeout': config('CACHE_REFRESH_TIMEOUT', default=30, cast=int),
        'max_retry_attempts': config('CACHE_MAX_RETRY_ATTEMPTS', default=3, cast=int),
        'retry_delay': config('CACHE_RETRY_DELAY', default=2, cast=int),
        'enable_monitoring': config('CACHE_ENABLE_MONITORING', default=True, cast=bool),
        'stale_if_error': config('CACHE_STALE_IF_ERROR', default=True, cast=bool)
    }

    # Security
    JWT_SECRET_KEY = config('JWT_SECRET_KEY', default=os.urandom(32).hex(), cast=str)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=config('JWT_ACCESS_TOKEN_EXPIRES', default=86400, cast=int)
    )

    # Firebase
    FIREBASE_CONFIG = {
        'project_id': config('FIREBASE_PROJECT_ID'),
        'private_key_id': config('FIREBASE_PRIVATE_KEY_ID'),
        'private_key': config('FIREBASE_PRIVATE_KEY').replace('\\n', '\n'),
        'client_email': config('FIREBASE_CLIENT_EMAIL'),
        'client_id': config('FIREBASE_CLIENT_ID'),
        'auth_uri': config('FIREBASE_AUTH_URI'),
        'token_uri': config('FIREBASE_TOKEN_URI')
    }

    # Microsoft SSO
    MICROSOFT_CONFIG = {
        'client_id': config('MICROSOFT_CLIENT_ID', default=None),
        'client_secret': config('MICROSOFT_CLIENT_SECRET', default=None),
        'tenant_id': config('MICROSOFT_TENANT_ID', default=None),
        'redirect_uri': config('MICROSOFT_REDIRECT_URI', default='http://localhost:5173/auth/microsoft/callback'),
        'scopes': ['openid', 'User.Read', 'https://graph.microsoft.com/User.Read'],
        'domain_hint': config('MICROSOFT_DOMAIN_HINT', default='aionmanagement.com'),
        'enabled': config('MICROSOFT_SSO_ENABLED', default='FALSE', cast=lambda x: x.upper() == 'TRUE')
    }

    # Session
    SESSION_CLEANUP_INTERVAL = config('SESSION_CLEANUP_INTERVAL', default=3600, cast=int)
    SESSION_MAX_AGE = config('SESSION_MAX_AGE', default=86400, cast=int)

    # Logging
    LOG_LEVEL = config('LOG_LEVEL', default='INFO')
    LOG_FILE_PATH = config('LOG_FILE_PATH', default='logs/api.log')
    LOG_FORMAT = config('LOG_FORMAT',
                        default='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    @classmethod
    def get_database_url(cls):
        return (
            f"mssql+pyodbc://{cls.DB_USER}:{cls.DB_PASSWORD}@"
            f"{cls.DB_SERVER}/{cls.DB_NAME}?"
            f"driver=ODBC+Driver+18+for+SQL+Server&"
            f"TrustServerCertificate=yes"
        )
