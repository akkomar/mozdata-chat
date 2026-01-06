#!/bin/bash

# Navigate to the proxy directory
cd "$(dirname "$0")/../proxy" || exit 1

# Activate the virtual environment
source .venv/bin/activate

# Run the proxy server
uv run main.py
