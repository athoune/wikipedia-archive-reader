.PHONY: help install build test clean dev lint format

# Default target
help:
	@echo "Wikipedia Archive Reader - Makefile targets:"
	@echo ""
	@echo "  make install   - Install the package in development mode"
	@echo "  make build     - Build the Rust extension with Maturin"
	@echo "  make test      - Run unit tests with pytest"
	@echo "  make clean     - Remove build artifacts and cache files"
	@echo "  make dev       - Install development dependencies"
	@echo "  make lint      - Run code quality checks"
	@echo "  make format    - Format code with black and rustfmt"
	@echo "  make rebuild   - Clean and rebuild (full rebuild)"
	@echo ""

# Install dependencies in virtual environment
install: 
	. .venv/bin/activate && \
	uv pip install -e ".[dev]"

# Build the Rust extension
build:
	. .venv/bin/activate && \
	maturin develop

# Run pytest on all tests
test: build
	. .venv/bin/activate && \
	pytest tests/ -v --tb=short

# Run tests with coverage
test-coverage: build
	. .venv/bin/activate && \
	pytest tests/ -v --cov=wikipedia_archive_reader --cov-report=html --cov-report=term

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache __pycache__ .coverage htmlcov/
	rm -rf target/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.so" -delete

# Install development dependencies
dev:
	. .venv/bin/activate && \
	uv pip install pytest maturin

# Lint Python code
lint:
	. .venv/bin/activate && \
	python -m py_compile wikipedia_archive_reader/*.py tests/*.py 2>&1 || true
	. .venv/bin/activate && \
	which pylint > /dev/null && pylint wikipedia_archive_reader/ tests/ || echo "pylint not installed, skipping"

# Format code
format:
	@echo "Formatting Rust code..."
	. .venv/bin/activate && \
	which rustfmt > /dev/null && rustfmt src/lib.rs || echo "rustfmt not available"
	@echo "Formatting Python code..."
	. .venv/bin/activate && \
	which black > /dev/null && black wikipedia_archive_reader/ tests/ || echo "black not installed, skipping"

# Full rebuild: clean and build
rebuild: clean build
	@echo "Rebuild complete"

# Quick test without rebuilding (for testing changes only)
test-quick:
	. .venv/bin/activate && \
	pytest tests/ -v

# Run a specific test
test-file:
	@echo "Usage: make test-file FILE=tests/test_archive_reader.py"

.venv:
	uv venv
