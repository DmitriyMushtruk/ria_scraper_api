#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Run database migrations
alembic upgrade head

# Start the server
exec uvicorn app.main:app --reload --reload-dir /app/app --host 0.0.0.0 --port 8000
