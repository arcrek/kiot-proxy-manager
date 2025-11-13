FROM python:3.11-alpine

WORKDIR /app

# Install build dependencies (will be removed after build)
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    libffi-dev \
    && apk add --no-cache \
    libffi

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && apk del .build-deps

# Copy application code
COPY app ./app

# Create necessary directories
RUN mkdir -p /app/data /app/traefik /app/logs

# Expose port
EXPOSE 8000

# Run with optimized settings
CMD ["python", "-u", "-OO", "-m", "app.main"]

