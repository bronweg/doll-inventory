# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Accept build arguments
ARG VITE_API_BASE_URL
ARG VITE_BAGS_COUNT

# Set environment variables for build
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_BAGS_COUNT=${VITE_BAGS_COUNT}

# Build the application
RUN npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

# Copy built files from builder
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./

# Copy entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Install vite for preview server
RUN npm install -g vite

# Expose port
EXPOSE 3000

# Set entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]

# Run the application
CMD ["vite", "preview", "--host", "0.0.0.0", "--port", "3000"]

