# Setup script for creating and activating virtual environment (PowerShell)

# Check if venv already exists
if (Test-Path "venv") {
    Write-Host "Virtual environment already exists."
} else {
    Write-Host "Creating virtual environment..."
    python -m venv venv
    Write-Host "Virtual environment created."
}

# Activate virtual environment
Write-Host "Activating virtual environment..."
& .\venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
Write-Host "Installing dependencies..."
pip install -r requirements.txt

# Install test dependencies
if (Test-Path "requirements-test.txt") {
    Write-Host "Installing test dependencies..."
    pip install -r requirements-test.txt
}

Write-Host ""
Write-Host "Setup complete! Virtual environment is activated."
Write-Host "To activate it manually in the future, run: .\venv\Scripts\Activate.ps1"

