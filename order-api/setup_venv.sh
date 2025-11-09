#!/bin/bash
# Setup script for creating and activating virtual environment

# Check if venv already exists
if [ -d "venv" ]; then
    echo "Virtual environment already exists."
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Install test dependencies
if [ -f "requirements-test.txt" ]; then
    echo "Installing test dependencies..."
    pip install -r requirements-test.txt
fi

echo ""
echo "Setup complete! Virtual environment is activated."
echo "To activate it manually in the future, run: source venv/bin/activate"

