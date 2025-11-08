# Makefile for order-api

.PHONY: help install venv run test lint lint-fix build clean

# ====================================================================================
# HELP
# ====================================================================================

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  help          Show this help message"
	@echo "  install       Install dependencies and setup virtual environment"
	@echo "  venv          Alias for install"
	@echo "  run           Run the FastAPI application in development mode"
	@echo "  test          Run tests with pytest"
	@echo "  lint          Lint code with ruff"
	@echo "  lint-fix      Fix linting errors with ruff"
	@echo "  build         Build the Docker image"
	@echo "  clean         Remove temporary files and virtual environment"


# ====================================================================================
# DEVELOPMENT
# ====================================================================================

# Check for virtual environment
VENV_DIR = venv
VENV_PYTHON = $(VENV_DIR)/bin/python

# Setup virtual environment and install dependencies
venv: $(VENV_DIR)/.installed

$(VENV_DIR)/.installed: requirements.txt requirements-test.txt
	@echo ">>> Creating/updating virtual environment and installing dependencies..."
	python3 -m venv $(VENV_DIR)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -r requirements.txt
	$(VENV_PYTHON) -m pip install -r requirements-test.txt
	@touch $(VENV_DIR)/.installed

install: venv

# Run the application
run: venv
	@echo ">>> Starting FastAPI application..."
	@$(VENV_PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# ====================================================================================
# TESTING & LINTING
# ====================================================================================

# Run tests
test: venv
	@echo ">>> Running tests..."
	@$(VENV_PYTHON) -m pytest

# Lint code
lint: venv
	@echo ">>> Linting code..."
	@$(VENV_PYTHON) -m ruff check .

# Fix linting errors
lint-fix: venv
	@echo ">>> Fixing linting errors..."
	@$(VENV_PYTHON) -m ruff check . --fix

# ====================================================================================
# DOCKER
# ====================================================================================

# Build Docker image
build:
	@echo ">>> Building Docker image..."
	@docker build -t order-api:latest .

# ====================================================================================
# CLEANUP
# ====================================================================================

# Clean temporary files
clean:
	@echo ">>> Cleaning up..."
	@rm -rf $(VENV_DIR)
	@rm -rf .pytest_cache
	@rm -rf .ruff_cache
	@find . -type d -name "__pycache__" -exec rm -r {} +
	@echo ">>> Cleanup complete."

