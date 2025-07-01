# VS Code Dev Container for OrderFox Development
# FastAPI Backend + Vanilla Frontend + Development Tools

FROM python:3.11-slim

# Install system dependencies including all required CLI tools
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    vim \
    nano \
    htop \
    procps \
    net-tools \
    supervisor \
    build-essential \
    sqlite3 \
    jq \
    tree \
    netcat-openbsd \
    telnet \
    ripgrep \
    fd-find \
    unzip \
    ca-certificates \
    gnupg \
    lsb-release \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 18 for frontend development
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Install global Node.js development tools
RUN npm install -g \
    wscat \
    http-server \
    npm-check-updates

# Create vscode user with sudo privileges for Dev Container
RUN groupadd --gid 1000 vscode \
    && useradd --uid 1000 --gid vscode --shell /bin/bash --create-home vscode \
    && echo vscode ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/vscode \
    && chmod 0440 /etc/sudoers.d/vscode

# Set up working directory
WORKDIR /workspace

# Install Python development tools
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    pytest \
    pytest-cov \
    black \
    flake8 \
    mypy \
    ipython \
    jupyter \
    debugpy

# Create necessary directories and set permissions
RUN mkdir -p /var/log/supervisor && \
    mkdir -p /workspace/logs && \
    chown -R vscode:vscode /workspace && \
    chmod -R 755 /workspace

# Switch to vscode user
USER vscode

# Set environment variables for development
ENV PYTHONPATH=/workspace
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