FROM python:3.12-bullseye

# Install system dependencies including SQL Server ODBC driver
RUN apt-get update && apt-get install -y \
    curl \
    gnupg2 \
    unixodbc \
    unixodbc-dev \
    && curl https://packages.microsoft.com/keys/microsoft.asc | tee /etc/apt/trusted.gpg.d/microsoft.asc \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Create .env file with default values
RUN echo "# Database Configuration\n\
DB_SERVER=\${DB_SERVER}\n\
DB_NAME=\${DB_NAME}\n\
DB_USER=\${DB_USER}\n\
DB_PASSWORD=\${DB_PASSWORD}\n\
\n\
# API Configuration\n\
API_HOST=\${API_HOST:-0.0.0.0}\n\
API_PORT=\${API_PORT:-5000}\n\
API_DEBUG=\${API_DEBUG:-False}\n\
\n\
# CORS Configuration\n\
CORS_ORIGINS=\${CORS_ORIGINS:-http://localhost:5173}\n\
CORS_MAX_AGE=\${CORS_MAX_AGE:-3600}\n\
\n\
# Cache Configuration\n\
CACHE_REFRESH_INTERVAL=\${CACHE_REFRESH_INTERVAL:-25}\n\
CACHE_FORCE_REFRESH=\${CACHE_FORCE_REFRESH:-3600}\n\
CACHE_REFRESH_TIMEOUT=\${CACHE_REFRESH_TIMEOUT:-30}\n\
CACHE_MAX_RETRY_ATTEMPTS=\${CACHE_MAX_RETRY_ATTEMPTS:-3}\n\
CACHE_RETRY_DELAY=\${CACHE_RETRY_DELAY:-5}\n\
CACHE_ENABLE_MONITORING=\${CACHE_ENABLE_MONITORING:-true}\n\
CACHE_LOG_REFRESHES=\${CACHE_LOG_REFRESHES:-true}\n\
CACHE_STALE_IF_ERROR=\${CACHE_STALE_IF_ERROR:-true}\n\
CACHE_EXPECTED_UPDATE_TIME=\${CACHE_EXPECTED_UPDATE_TIME:-15:00}\n\
CACHE_UPDATE_WINDOW=\${CACHE_UPDATE_WINDOW:-7200}\n\
\n\
# Firebase Configuration\n\
FIREBASE_PROJECT_ID=\${FIREBASE_PROJECT_ID:-}\n\
FIREBASE_PRIVATE_KEY_ID=\${FIREBASE_PRIVATE_KEY_ID:-}\n\
FIREBASE_PRIVATE_KEY=\${FIREBASE_PRIVATE_KEY:-}\n\
FIREBASE_CLIENT_EMAIL=\${FIREBASE_CLIENT_EMAIL:-}\n\
FIREBASE_CLIENT_ID=\${FIREBASE_CLIENT_ID:-}\n\
FIREBASE_AUTH_URI=\${FIREBASE_AUTH_URI:-https://accounts.google.com/o/oauth2/auth}\n\
FIREBASE_TOKEN_URI=\${FIREBASE_TOKEN_URI:-https://oauth2.googleapis.com/token}\n\
\n\
# Session Configuration\n\
SESSION_CLEANUP_INTERVAL=\${SESSION_CLEANUP_INTERVAL:-300}\n\
SESSION_MAX_AGE=\${SESSION_MAX_AGE:-1800}\n\
\n\
# Logging Configuration\n\
LOG_LEVEL=\${LOG_LEVEL:-INFO}\n\
LOG_FILE_PATH=\${LOG_FILE_PATH:-logs/api.log}\n\
LOG_FORMAT=\${LOG_FORMAT:-\"%(asctime)s - %(name)s - %(levelname)s - %(message)s\"}\n\
\n\
# Microsoft SSO Configuration\n\
MICROSOFT_SSO_ENABLED=\${MICROSOFT_SSO_ENABLED:-FALSE}\n\
MICROSOFT_CLIENT_ID=\${MICROSOFT_CLIENT_ID:-}\n\
MICROSOFT_CLIENT_SECRET=\${MICROSOFT_CLIENT_SECRET:-}\n\
MICROSOFT_TENANT_ID=\${MICROSOFT_TENANT_ID:-}\n\
MICROSOFT_REDIRECT_URI=\${MICROSOFT_REDIRECT_URI:-http://localhost:5173/api/auth/microsoft/callback}\n\
MICROSOFT_DOMAIN_HINT=\${MICROSOFT_DOMAIN_HINT:-}\n\
\n\
FRONTEND_URL=\${FRONTEND_URL:-http://localhost:5173}" > /app/.env

# Create log directory
RUN mkdir -p /app/logs

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 5000

# Run uvicorn with factory pattern
CMD ["uvicorn", "app:create_asgi_app", "--host", "0.0.0.0", "--port", "5000", "--factory"]