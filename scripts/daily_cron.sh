#!/usr/bin/env bash
# Script for scheduled daily execution via cron or systemd timer
set -e

# Directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( dirname "$SCRIPT_DIR" )"

cd "$PROJECT_DIR"

if [ -f ".venv/bin/python3" ]; then
    PYTHON_EXEC=".venv/bin/python3"
else
    PYTHON_EXEC="python3"
fi

echo "[$(date)] Running Personal AI Daily Newspaper Pipeline..."
$PYTHON_EXEC main.py >> data/newspaper.log 2>&1
echo "[$(date)] Daily Newspaper Pipeline completed."
