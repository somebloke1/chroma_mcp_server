#!/bin/bash

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Function to install specific version
install_version() {
    local version=$1
    echo "Installing chroma-mcp-server version $version..."
    uvx pip install --upgrade "chroma-mcp-server==${version}"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install version $version"
        exit 1
    fi
    echo "Successfully installed version $version"
}

# Function to update version in mcp.json
update_mcp_json() {
    local version=$1
    local mcp_json="${PROJECT_ROOT}/.cursor/mcp.json"
    
    if [ ! -f "$mcp_json" ]; then
        echo "Error: mcp.json not found at $mcp_json"
        exit 1
    fi

    # Create a temporary file
    tmp_file=$(mktemp)
    
    # Read the current version from pyproject.toml if not provided
    if [ -z "$version" ]; then
        version=$(grep '^version = ' "${PROJECT_ROOT}/pyproject.toml" | cut -d'"' -f2)
        if [ -z "$version" ]; then
            echo "Error: Could not determine version from pyproject.toml"
            exit 1
        fi
    fi

    # Update the version in mcp.json (now just the server command)
    cat "$mcp_json" | jq '
        .mcpServers.chroma.command = "uvx" |
        .mcpServers.chroma.args = ["chroma-mcp-server"]
    ' > "$tmp_file"

    # Check if jq succeeded
    if [ $? -ne 0 ]; then
        echo "Error: Failed to update mcp.json"
        rm "$tmp_file"
        exit 1
    fi

    # Move the temporary file to the original
    mv "$tmp_file" "$mcp_json"
    echo "Successfully updated mcp.json configuration"
}

# Print usage
usage() {
    echo "Usage: $0 [-i] VERSION"
    echo "  -i    Install the specified version"
    echo "  -h    Show this help message"
    echo ""
    echo "If version is not provided, it will be read from pyproject.toml"
    exit 0
}

# Main script
install=false

while getopts "hi" opt; do
    case $opt in
        h)
            usage
            ;;
        i)
            install=true
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            usage
            ;;
    esac
done

shift $((OPTIND-1))
version=$1

# If no version provided, try to get from pyproject.toml
if [ -z "$version" ]; then
    version=$(grep '^version = ' "${PROJECT_ROOT}/pyproject.toml" | cut -d'"' -f2)
    if [ -z "$version" ]; then
        echo "Error: No version provided and could not determine version from pyproject.toml"
        exit 1
    fi
fi

# If install flag is set, install the version
if [ "$install" = true ]; then
    install_version "$version"
fi

# Always update the mcp.json configuration
update_mcp_json "$version"

echo "
Version management complete. To use this version:

1. If you haven't installed the package yet, run:
   $0 -i $version

2. Restart Cursor to apply the changes

The server will now run using uvx with version $version" 