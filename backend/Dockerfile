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

# Create log directory with proper permissions for root user
RUN mkdir -p /app/logs && \
    chown -R root:root /app/logs && \
    chmod -R 755 /app/logs && \
    chmod g+s /app/logs  # Set SGID bit to maintain group ownership

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 5000

# Run uvicorn with factory pattern
CMD ["uvicorn", "app:create_asgi_app", "--host", "0.0.0.0", "--port", "5000", "--factory"]