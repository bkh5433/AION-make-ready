# Build stage
FROM node:20-alpine as builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Create a minimal container to hold the built files
FROM alpine:latest

# Create www-data user (group may already exist)
RUN adduser -S -G www-data www-data 2>/dev/null || adduser -S -g www-data www-data

# Install rsync and su-exec for file copying and privilege dropping
RUN apk add --no-cache rsync su-exec

# Set working directory
WORKDIR /app

# Copy built files from builder stage
COPY --from=builder /app/dist /app

# Set ownership of the app directory
RUN chown -R www-data:www-data /app

# Create the entrypoint script properly
RUN printf '#!/bin/sh\n\
\n\
echo "Starting frontend file sync service..."\n\
\n\
# Initial sync\n\
echo "Performing initial sync..."\n\
rsync -av --delete /app/ /var/www/html/\n\
\n\
# Continuous sync\n\
echo "Starting continuous sync..."\n\
while true; do\n\
    echo "Checking for changes..."\n\
    rsync -av --delete /app/ /var/www/html/\n\
    sleep 5\n\
done\n' > /entrypoint.sh && \
    chmod +x /entrypoint.sh && \
    chown www-data:www-data /entrypoint.sh

# Container will start as root but drop to www-data via docker-compose entrypoint
CMD ["/entrypoint.sh"] 