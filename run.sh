#!/bin/bash
# Start Redline Reveal locally
# Usage: bash run.sh
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/backend"

echo "Starting Redline Reveal at http://localhost:8080"
.venv/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload
