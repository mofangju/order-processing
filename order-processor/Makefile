.PHONY: help test coverage fmt fmt-check lint build clean ci deps

# Variables
GO := go
BIN := bin/processor
COVERAGE_FILE := coverage.out

# Default target
.DEFAULT_GOAL := help

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  test        Run unit tests"
	@echo "  coverage    Run tests and show coverage"
	@echo "  fmt         Format code"
	@echo "  fmt-check   Fail if code is not formatted"
	@echo "  lint        Run golangci-lint (installs if missing)"
	@echo "  build       Build binary to $(BIN)"
	@echo "  clean       Remove build artifacts"

test:
	@echo "Running tests..."
	@$(GO) test ./... -v -race

coverage:
	@echo "Running tests with coverage..."
	@$(GO) test ./... -coverprofile=$(COVERAGE_FILE)
	@$(GO) tool cover -func=$(COVERAGE_FILE)

fmt:
	@echo "Formatting code..."
	@$(GO) fmt ./...

fmt-check:
	@echo "Checking formatting..."
	@if [ $$(gofmt -l . | wc -l) -ne 0 ]; then \
		echo "Code not formatted. Run 'make fmt'."; \
		gofmt -l .; \
		exit 1; \
	fi
	@echo "Formatting OK"

lint:
	@echo "Running golangci-lint..."
	@if command -v golangci-lint >/dev/null 2>&1; then \
		golangci-lint run ./...; \
	else \
		echo "golangci-lint not found. Installing to $$(go env GOPATH)/bin..."; \
		curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $$(go env GOPATH)/bin latest; \
		$$(go env GOPATH)/bin/golangci-lint run ./...; \
	fi

build:
	@echo "Building binary..."
	@mkdir -p $(dir $(BIN))
	@$(GO) build -o $(BIN) ./cmd/processor
	@echo "Built $(BIN)"

clean:
	@echo "Cleaning..."
	@rm -rf $(BIN) $(COVERAGE_FILE)
	@echo "Done"

deps:
	@echo "Ensuring Go modules (go.mod/go.sum)..."
	@$(GO) mod tidy

ci: deps fmt-check lint test
	@echo "CI checks passed"


