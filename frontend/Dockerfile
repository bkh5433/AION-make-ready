FROM node:18-alpine as builder

# Set working directory
WORKDIR /app

# Update npm to latest version
RUN npm install -g npm@latest

# Copy package files
COPY package.json ./

# Install dependencies and generate new package-lock.json
RUN npm install

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Keep the container running to maintain the volume mount
CMD ["tail", "-f", "/dev/null"] 