#!/bin/bash

# Start PostgreSQL test database using Docker Compose

set -e

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Starting PostgreSQL test database..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Start only the PostgreSQL test service
cd "$PROJECT_ROOT"
docker-compose up -d postgres-test

# Wait for database to be ready
echo "Waiting for database to be ready..."
timeout=30
elapsed=0

while [ $elapsed -lt $timeout ]; do
    if docker-compose exec -T postgres-test pg_isready -U orderfox_test_user -d orderfox_test_db > /dev/null 2>&1; then
        echo "✓ PostgreSQL test database is ready!"
        echo "  - Host: localhost"
        echo "  - Port: 5433"  
        echo "  - Database: orderfox_test_db"
        echo "  - User: orderfox_test_user"
        echo "  - Password: orderfox_test_password"
        echo ""
        echo "You can now run database tests with:"
        echo "  cd backend && python -m pytest tests/test_database.py -v"
        exit 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
done

echo "Error: Database failed to start within $timeout seconds"
exit 1