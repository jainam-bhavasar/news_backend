#!/bin/bash

# Create Python virtual environment
echo "Creating Python virtual environment..."
python3 -m venv .venv

# Activate the virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install requirements
echo "Installing requirements..."
python3 -m pip install -r requirements.txt

echo "Setup complete! Virtual environment is activated and requirements are installed." 