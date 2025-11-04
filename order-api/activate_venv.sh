#!/bin/bash
# Quick activation script for virtual environment

if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Run setup_venv.sh first."
    exit 1
fi

source venv/bin/activate
echo "Virtual environment activated!"

