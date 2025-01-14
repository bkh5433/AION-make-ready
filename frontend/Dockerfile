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

# Set working directory
WORKDIR /app

# Copy built files from builder stage
COPY --from=builder /app/dist /app

# Keep container running
CMD ["tail", "-f", "/dev/null"] 