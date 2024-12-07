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
COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY .. .

# Create .env file with default values
RUN echo "CACHE_REFRESH_INTERVAL=36000\n\
CACHE_FORCE_REFRESH=43200\n\
CACHE_REFRESH_TIMEOUT=30\n\
CACHE_MAX_RETRY_ATTEMPTS=3\n\
CACHE_RETRY_DELAY=2\n\
CACHE_ENABLE_MONITORING=True\n\
CACHE_STALE_IF_ERROR=True" > /app/.env

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 5000

# Run gunicorn
CMD ["gunicorn", "--bind=0.0.0.0:5000", "--chdir=/app", "app:app"]