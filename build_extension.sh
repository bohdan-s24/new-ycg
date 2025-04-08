#!/bin/bash
# Simple script to build the extension for testing

echo "Building YouTube Chapter Generator extension..."

# Create a dist directory if it doesn't exist
mkdir -p dist

# Copy all necessary files to the dist directory
cp -r extension/* dist/

echo "Extension built successfully. Load the 'dist' folder in Chrome's extension page."
