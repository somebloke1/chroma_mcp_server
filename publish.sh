#!/bin/bash
# Script to build and publish the package to PyPI

# ANSI color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================================================${NC}"
echo -e "${BLUE}            Building and Publishing Chroma MCP Server            ${NC}"
echo -e "${BLUE}=================================================================${NC}"

# Check if build is installed
if ! python -c "import build" &> /dev/null; then
    echo -e "${YELLOW}The 'build' package is not installed. Installing it now...${NC}"
    pip install build
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to install 'build'. Please install it manually:${NC}"
        echo -e "${RED}pip install build${NC}"
        exit 1
    fi
fi

# Check if twine is installed
if ! python -c "import twine" &> /dev/null; then
    echo -e "${YELLOW}The 'twine' package is not installed. Installing it now...${NC}"
    pip install twine
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to install 'twine'. Please install it manually:${NC}"
        echo -e "${RED}pip install twine${NC}"
        exit 1
    fi
fi

# Clean up previous builds
echo -e "${YELLOW}Cleaning up previous builds...${NC}"
rm -rf dist/ build/ *.egg-info/

# Build the package
echo -e "${YELLOW}Building the package...${NC}"
python -m build

# Check if build was successful
if [ $? -ne 0 ]; then
    echo -e "${RED}Build failed. Exiting.${NC}"
    echo -e "${RED}Detailed build command that should work:${NC}"
    echo -e "${RED}python -m pip install --upgrade pip setuptools wheel build${NC}"
    echo -e "${RED}python -m build${NC}"
    exit 1
fi

echo -e "${YELLOW}Package built successfully.${NC}"

# Ask for confirmation before publishing
read -p "Do you want to publish to PyPI? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Use twine to upload to PyPI
    echo -e "${YELLOW}Publishing to PyPI...${NC}"
    python -m twine upload dist/*
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Upload failed. Make sure you have proper credentials.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}=================================================================${NC}"
    echo -e "${GREEN}                  Package Published Successfully!                 ${NC}"
    echo -e "${GREEN}=================================================================${NC}"
    echo -e "${GREEN}The Chroma MCP Server package is now available on PyPI.          ${NC}"
    echo -e "${GREEN}Users can run it with: uvx chroma-mcp-server                     ${NC}"
    echo -e "${GREEN}=================================================================${NC}"
else
    echo -e "${YELLOW}Publish canceled.${NC}"
    echo -e "${BLUE}You can test the package locally with:${NC}"
    echo -e "${BLUE}pip install -e .${NC}"
    echo -e "${BLUE}or${NC}"
    echo -e "${BLUE}pip install dist/*.whl${NC}"
fi 