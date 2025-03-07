#!/bin/bash

# Script to install Python requirements for the Flask application
# Make this script executable with: chmod +x install_requirements.sh

echo "Starting installation of requirements..."

# Install requirements
echo "Installing requirements from requirements.txt..."
pip install -r requirements.txt


echo "Done."