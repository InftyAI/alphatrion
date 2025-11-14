#!/usr/bin/env bash
set -euo pipefail

# Activate the uv-managed virtual environment.
# Make sure you've run `uv sync` once before sourcing this script.
if [ ! -d ".venv" ]; then
  echo "No .venv directory found. Please run 'uv sync' first to create the virtual environment."
  exit 1
fi

# shellcheck source=/dev/null
source .venv/bin/activate
