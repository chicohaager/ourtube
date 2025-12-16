# Multi-stage build for optimized image size
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Alpine-based Python for smaller image
FROM python:3.12-alpine

# Install ffmpeg and build dependencies
RUN apk add --no-cache \
    ffmpeg \
    curl \
    && rm -rf /var/cache/apk/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/*.py ./backend/
COPY backend/requirements.txt ./backend/

# Copy frontend build
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create downloads directory
RUN mkdir -p /app/downloads /app/config

# Expose port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/config || exit 1

# Start the application
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]