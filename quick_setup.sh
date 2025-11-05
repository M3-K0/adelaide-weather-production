#!/bin/bash
# Quick setup for Adelaide Weather Forecasting System

echo "🚀 Setting up Adelaide Weather Forecasting System"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install minimal required packages
echo "Installing packages..."
pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install numpy pandas

echo "✅ Quick setup complete!"
echo "To activate: source .venv/bin/activate"