#!/usr/bin/env bash

# if .venv does not exist, create it and install dependencies
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment and installing dependencies..."
    uv venv
    source .venv/bin/activate
    uv sync
else
    echo "Virtual environment already exists. Activating..."
    source .venv/bin/activate
fi
