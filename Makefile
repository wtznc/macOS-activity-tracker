.PHONY: help install install-dev test test-cov lint format clean build release app

# Default target
help:
	@echo "Available commands:"
	@echo "  install      Install package in development mode"
	@echo "  install-dev  Install package with development dependencies"
	@echo "  test         Run tests"
	@echo "  test-cov     Run tests with coverage report"
	@echo "  lint         Run linting checks"
	@echo "  format       Format code with black and isort"
	@echo "  clean        Clean build artifacts"
	@echo "  build        Build package"
	@echo "  release      Build and release package"
	@echo "  app          Build macOS app bundle"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

# Testing
test:
	pytest

test-cov:
	pytest --cov=activity_tracker --cov-report=html --cov-report=term

# Code quality
lint:
	flake8 src tests
	mypy src
	black --check src tests
	isort --check-only src tests

format:
	black src tests
	isort src tests

# Pre-commit
pre-commit:
	pre-commit run --all-files

# Build and release
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

release: build
	python -m twine upload dist/*

# macOS app bundle
app:
	./scripts/build-app.sh