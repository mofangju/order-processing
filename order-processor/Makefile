.PHONY: help test test-verbose test-coverage lint fmt vet clean build install-tools

# Variables
GO_VERSION := 1.24
COVERAGE_FILE := coverage.out
COVERAGE_HTML := coverage.html

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

test: ## Run unit tests
	@echo "Running unit tests..."
	@go test -v -race ./...

test-verbose: ## Run unit tests with verbose output
	@echo "Running unit tests (verbose)..."
	@go test -v -race -count=1 ./...

test-coverage: ## Run tests with coverage report
	@echo "Running tests with coverage..."
	@go test -v -race -coverprofile=$(COVERAGE_FILE) ./...
	@go tool cover -func=$(COVERAGE_FILE)
	@echo ""
	@echo "Coverage report saved to $(COVERAGE_FILE)"
	@echo "To view HTML report, run: make coverage-html"

coverage-html: test-coverage ## Generate HTML coverage report
	@echo "Generating HTML coverage report..."
	@go tool cover -html=$(COVERAGE_FILE) -o $(COVERAGE_HTML)
	@echo "HTML coverage report saved to $(COVERAGE_HTML)"

lint: ## Run golangci-lint (requires golangci-lint to be installed)
	@echo "Running golangci-lint..."
	@if command -v golangci-lint >/dev/null 2>&1; then \
		golangci-lint run ./...; \
	else \
		echo "golangci-lint not found. Installing latest version..."; \
		curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $$(go env GOPATH)/bin latest; \
		golangci-lint run ./...; \
	fi

lint-install: ## Install golangci-lint
	@echo "Installing golangci-lint..."
	@curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $$(go env GOPATH)/bin latest
	@echo "golangci-lint installed to $$(go env GOPATH)/bin"

fmt: ## Format Go code
	@echo "Formatting Go code..."
	@go fmt ./...
	@echo "Code formatted"

fmt-check: ## Check if code is formatted (fails if not)
	@echo "Checking code formatting..."
	@if [ $$(gofmt -l . | wc -l) -ne 0 ]; then \
		echo "Code is not formatted. Run 'make fmt' to fix."; \
		gofmt -l .; \
		exit 1; \
	fi
	@echo "Code is properly formatted"

vet: ## Run go vet
	@echo "Running go vet..."
	@go vet ./...

mod-tidy: ## Tidy go modules
	@echo "Tidying go modules..."
	@go mod tidy
	@go mod verify

mod-download: ## Download go modules
	@echo "Downloading go modules..."
	@go mod download

build: ## Build the processor binary
	@echo "Building processor..."
	@go build -o bin/processor ./cmd/processor
	@echo "Binary built: bin/processor"

clean: ## Clean build artifacts
	@echo "Cleaning..."
	@rm -rf bin/
	@rm -f $(COVERAGE_FILE) $(COVERAGE_HTML)
	@echo "Clean complete"

install-tools: ## Install development tools (golangci-lint)
	@echo "Installing development tools..."
	@make lint-install
	@echo "Tools installed"

check: fmt-check vet test ## Run all checks (format, vet, tests)

ci: mod-tidy fmt-check vet lint test-coverage ## Run CI checks (for CI/CD pipelines)

all: clean mod-tidy fmt vet lint test-coverage build ## Run all: clean, tidy, format, vet, lint, test, and build


