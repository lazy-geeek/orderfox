#!/bin/bash

# Stop PostgreSQL test database using Docker Compose

set -e

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Stopping PostgreSQL test database..."

# Stop only the PostgreSQL test service
cd "$PROJECT_ROOT"
docker-compose stop postgres-test

echo "✓ PostgreSQL test database stopped"