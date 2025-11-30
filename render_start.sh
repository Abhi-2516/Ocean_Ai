#!/usr/bin/env bash
set -e

# If you want to ingest assets on deploy (recommended for Render ephemeral instances),
# run ingest_runner for asset files if present. Errors are tolerated.
if [ -d "./assets" ]; then
  python backend/ingest_runner.py $(ls assets/* 2>/dev/null || true) || true
fi

# Start uvicorn on the port Render provides
exec uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000}
