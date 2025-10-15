# Build stage
FROM node:20-alpine as builder

WORKDIR /app

# Build-time env for Vite bundling (default to backend service URL)
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Copy package files
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Build the application (Vite picks up VITE_* env)
RUN npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

# Runtime env for the static bundle (kept for consistency)
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Install serve for production
RUN npm install -g serve

# Copy built application from builder
COPY --from=builder /app/build /app/build

# Create non-root user
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001
USER nodejs

# Expose port
EXPOSE 3000

# Serve the application
CMD ["serve", "-s", "build", "-l", "3000"]

