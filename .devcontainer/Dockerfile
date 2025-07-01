# VS Code Dev Container for OrderFox Development
# FastAPI Backend + Vanilla Frontend + Development Tools

FROM python:3.11-slim

# Install system dependencies (avoiding duplicates with common-utils feature)
# Include development libraries to ensure Python wheels are available
RUN apt-get update && apt-get install -y \
    supervisor \
    build-essential \
    sqlite3 \
    netcat-openbsd \
    telnet \
    ripgrep \
    fd-find \
    libffi-dev \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 for frontend development (required for Vite 7.0.0+)
RUN apt-get update && apt-get install -y curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get remove -y curl \
    && rm -rf /var/lib/apt/lists/*

# Install global Node.js development tools
RUN npm install -g \
    wscat \
    http-server \
    npm-check-updates

# User creation handled by common-utils feature

# Set up working directory
WORKDIR /workspaces/orderfox

# Install Python development tools (prefer pre-built wheels to avoid compilation)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --prefer-binary \
    pytest \
    pytest-cov \
    black \
    ipython \
    jupyter \
    debugpy

# Pre-install problematic packages that often compile from source
# Using --only-binary to force wheel usage and avoid compilation
RUN pip install --no-cache-dir --only-binary=:all: \
    cryptography==45.0.2 \
    grpcio==1.71.0 \
    google-crc32c==1.7.1 \
    pydantic_core==2.33.2 \
    cffi==1.17.1 \
    pycares==4.8.0 \
    websockets==12.0 \
    msgpack==1.1.0 \
    || echo "⚠️  Some wheels not available, will compile during requirements install"

# Create necessary directories (user creation handled by common-utils feature)
RUN mkdir -p /var/log/supervisor && \
    mkdir -p /workspaces/orderfox/logs && \
    chmod -R 755 /workspaces/orderfox

# User switching handled by devcontainer feature

# Set environment variables for development
ENV PYTHONPATH=/workspaces/orderfox
ENV NODE_ENV=development
ENV ENVIRONMENT=development
ENV DEBUG=true
ENV DEVCONTAINER_MODE=true

# Expose ports for development services
# 8000: FastAPI backend
# 3000: Vite dev server
# 5678: Python debugpy
# 8080: Alternative port for services
EXPOSE 8000 3000 5678 8080

# Default command - keep container running
CMD ["sleep", "infinity"]