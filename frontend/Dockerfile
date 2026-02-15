# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

# Copy built files from builder
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./

# Install vite for preview server
RUN npm install -g vite

# Expose port
EXPOSE 3000

# Run the application
CMD ["vite", "preview", "--host", "0.0.0.0", "--port", "3000"]

