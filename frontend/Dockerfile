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

# Install rsync for file copying
RUN apk add --no-cache rsync

# Set working directory
WORKDIR /app

# Copy built files from builder stage
COPY --from=builder /app/dist /app

# Add script to sync files and keep container running
RUN echo '#!/bin/sh\nwhile true; do\n  rsync -av --delete /app/ /var/www/html/\n  sleep 5\ndone' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Keep container running and sync files
CMD ["/entrypoint.sh"] 