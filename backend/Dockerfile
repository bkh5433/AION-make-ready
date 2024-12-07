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

# Copy the backend package
COPY src/aion /app/aion
COPY app.py /app/
COPY config.py /app/
COPY auth_middleware.py /app/
COPY cache_module.py /app/
COPY logger_config.py /app/
COPY monitoring.py /app/
COPY queue_manager.py /app/

# Set Python path
ENV PYTHONPATH=/app

# Run gunicorn
CMD ["gunicorn", "--bind=0.0.0.0:5000", "--chdir=/app", "app:app"]