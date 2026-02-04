#!/bin/bash
set -e

echo "🐍 Installing Python dependencies..."

# Upgrade pip
pip install --upgrade pip

# Install tox for multi-version testing
pip install tox

# Install test dependencies
pip install -r tests/requirements.txt

# Install the package in editable mode
pip install -e .

echo "✅ Dev container setup complete!"
echo ""
echo "Available commands:"
echo "  - pytest tests/        # Run tests"
echo "  - ./run_tests.sh       # Run tests with virtual env"
echo "  - tox                  # Run tests across Python versions"
echo "  - black .              # Format code"
echo "  - pylint srt.py        # Lint code"
echo "  - claude               # Claude Code CLI"
