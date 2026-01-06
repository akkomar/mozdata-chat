#!/bin/bash

# Navigate to the proxy directory
cd "$(dirname "$0")/../proxy" || exit 1

uv sync
