#!/bin/bash

# Run unit tests for the social media keyword alert SaaS application
echo "Running unit tests..."

# Create test directory if it doesn't exist
mkdir -p tests

# Install test dependencies
pip install flask-testing pytest pytest-cov

# Run tests with coverage
python -m pytest tests/ -v --cov=app

# Check exit code
if [ $? -eq 0 ]; then
    echo "All tests passed successfully!"
    exit 0
else
    echo "Some tests failed. Please check the output above for details."
    exit 1
fi
