FROM node:20-alpine as builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Keep the container running to maintain the volume mount
CMD ["tail", "-f", "/dev/null"] 