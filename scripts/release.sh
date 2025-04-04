#!/bin/bash
# Wrapper script to automate the release process for chroma-mcp-server

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PACKAGE_NAME="chroma-mcp-server"
PYPI_URL="https://pypi.org/pypi"
TESTPYPI_URL="https://test.pypi.org/pypi"

# --- Dependency Check ---
if ! command -v curl &> /dev/null; then
    echo "❌ ERROR: curl is required but not found. Please install curl." >&2
    exit 1
fi
if ! command -v jq &> /dev/null; then
    echo "❌ ERROR: jq is required but not found. Please install jq (e.g., brew install jq)." >&2
    exit 1
fi

# --- Argument Parsing ---
VERSION=""
SKIP_TESTPYPI=false
TEST_ONLY=false
YES_FLAG=false
UPDATE_TARGET="prod" # New: prod or test

usage() {
    echo "Usage: $0 [-h] [-y] [--skip-testpypi] [--test-only] [--update-target <prod|test>] VERSION"
    echo ""
    echo "Automates the release process: TestPyPI build & test -> Prod PyPI build & publish -> Update Cursor Config."
    echo ""
    echo "Arguments:"
    echo "  VERSION          The version number to release (e.g., 0.1.7)"
    echo ""
    echo "Options:"
    echo "  -h, --help       Show this help message and exit."
    echo "  -y, --yes        Automatically answer yes to confirmation prompts."
    echo "  --skip-testpypi  Skip the TestPyPI build and local install test steps."
    echo "  --test-only      Only perform the TestPyPI build and local install test, then exit."
    echo "  --update-target <prod|test>  Install version from prod (PyPI) or test (TestPyPI) for Cursor use (default: prod)."
    exit 0
}

# --- Helper Functions ---
check_if_version_exists() {
    local pkg_name="$1"
    local version_to_check="$2"
    local index_url="$3"
    local index_name="$4"

    echo "  Checking if version $version_to_check exists on $index_name..."
    # Use curl to get package info, jq to check if version exists in releases
    if curl -s "$index_url/$pkg_name/$version_to_check/json" | jq -e '(.info.version == "'"$version_to_check"'")' > /dev/null; then
        echo "  ❌ ERROR: Version $version_to_check already exists on $index_name!" >&2
        return 1 # Indicate failure (version exists)
    else
        # Check if the overall package fetch failed (e.g., 404), indicating version likely doesn't exist
        if ! curl -s -f "$index_url/$pkg_name/json" > /dev/null; then
             echo "  Package $pkg_name not found on $index_name (or network error). Assuming version $version_to_check does not exist."
             return 0 # Indicate success (version likely doesn't exist)
        fi
        echo "  Version $version_to_check does not appear to exist on $index_name. Proceeding."
        return 0 # Indicate success (version does not exist)
    fi
}

# --- Main Script Logic ---

# Simple argument parsing loop
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -h|--help)
            usage
            ;;
        -y|--yes)
            YES_FLAG=true
            shift # past argument
            ;;
        --skip-testpypi)
            SKIP_TESTPYPI=true
            shift # past argument
            ;;
        --test-only)
            TEST_ONLY=true
            shift # past argument
            ;;
        --update-target)
            if [[ "$2" == "prod" || "$2" == "test" ]]; then
                UPDATE_TARGET="$2"
                shift # past argument
                shift # past value
            else
                echo "Error: --update-target must be 'prod' or 'test'"
                usage
            fi
            ;;
        *)    # unknown option assumed to be VERSION
            if [ -z "$VERSION" ]; then
                VERSION="$1"
            else
                echo "Error: Unknown option or multiple versions specified: $1"
                usage
            fi
            shift # past argument
            ;;
    esac
done

# Validate VERSION
if [ -z "$VERSION" ]; then
    echo "Error: VERSION is required."
    usage
fi
# Basic version format check (adjust regex if needed)
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([a-zA-Z0-9.-]*)?$ ]]; then
    echo "Error: Invalid version format: $VERSION (Expected X.Y.Z or similar)"
    exit 1
fi

echo "🚀 Starting Release Process for Version: $VERSION"
echo "--------------------------------------------------"
echo "Configuration:"
echo "  Skip TestPyPI Build/Test: $SKIP_TESTPYPI"
echo "  TestPyPI Only:            $TEST_ONLY"
echo "  Update Target for Cursor: $UPDATE_TARGET"
echo "  Non-interactive:          $YES_FLAG"
echo "--------------------------------------------------"

# Confirmation prompt
if [ "$YES_FLAG" = false ]; then
    read -p "Proceed with this release plan? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Release cancelled by user."
        exit 1
    fi
fi

# --- TestPyPI Phase ---
if [ "$SKIP_TESTPYPI" = false ]; then
    echo ""
    echo "📦 Phase 1: Building and Publishing to TestPyPI..."
    
    # Check if version already exists on TestPyPI BEFORE publishing
    check_if_version_exists "$PACKAGE_NAME" "$VERSION" "$TESTPYPI_URL" "TestPyPI"
    if [ $? -ne 0 ]; then exit 1; fi # Exit if version exists

    # Call publish script (which updates pyproject.toml)
    echo "  Calling publish.sh to build and publish to TestPyPI..."
    "${SCRIPT_DIR}/publish.sh" -t -y -v "$VERSION"
    if [ $? -ne 0 ]; then echo "❌ ERROR: Failed to publish to TestPyPI."; exit 1; fi
    echo "✅ Successfully published to TestPyPI."

    echo ""
    echo "🔧 Phase 2: Testing Local Installation..."
    "${SCRIPT_DIR}/test_uvx_install.sh"
    if [ $? -ne 0 ]; then echo "❌ ERROR: Local installation test failed."; exit 1; fi
    echo "✅ Local installation test successful."

    if [ "$TEST_ONLY" = true ]; then
        echo ""
        echo "✅ TestPyPI phase complete (--test-only specified). Exiting."
        exit 0
    fi
else
    echo "⏩ Skipping TestPyPI build and test phases."
fi

# --- Production Phase ---
echo ""
echo "📦 Phase 3: Building and Publishing to Production PyPI..."

# Check if version already exists on Production PyPI BEFORE publishing
check_if_version_exists "$PACKAGE_NAME" "$VERSION" "$PYPI_URL" "Production PyPI"
if [ $? -ne 0 ]; then exit 1; fi # Exit if version exists

# Extra confirmation for production unless -y is set
if [ "$YES_FLAG" = false ]; then
    read -p "🚨 REALLY publish version $VERSION to Production PyPI? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Production release cancelled by user."
        exit 1
    fi
fi

# Call publish script (which updates pyproject.toml again if needed, harmless)
"${SCRIPT_DIR}/publish.sh" -p -y -v "$VERSION"
if [ $? -ne 0 ]; then echo "❌ ERROR: Failed to publish to Production PyPI."; exit 1; fi
echo "✅ Successfully published to Production PyPI."

# --- Update Phase ---
echo ""
echo "🔧 Phase 4: Installing Release Version for Local UVX (Target: $UPDATE_TARGET)..."

INSTALL_ARGS=""
STRATEGY_ARG=""
PACKAGE_SPEC="$PACKAGE_NAME@$VERSION"

if [ "$UPDATE_TARGET" == "test" ]; then
    echo "  Installing version $VERSION from TestPyPI for local uvx command..."
    INSTALL_ARGS="--default-index $TESTPYPI_URL --index $PYPI_URL"
    STRATEGY_ARG="--index-strategy unsafe-best-match"
else
    echo "  Installing version $VERSION from PyPI for local uvx command..."
    INSTALL_ARGS="--default-index $PYPI_URL" # Explicitly use PyPI
fi

install_command="uvx ${INSTALL_ARGS} ${STRATEGY_ARG} ${PACKAGE_SPEC}"
echo "  Running: $install_command"
eval $install_command # Use eval to handle args correctly

if [ $? -ne 0 ]; then echo "❌ ERROR: Failed to install $UPDATE_TARGET version $VERSION locally via uvx."; exit 1; fi
echo "  ✅ $UPDATE_TARGET version $VERSION installed for local uvx command."

echo "  Refreshing local UVX cache (may not be necessary with direct install)..."
if command -v uvx &> /dev/null; then
    # Refresh might still help ensure internal links are updated
    uvx --refresh $PACKAGE_NAME --version 
    echo "  ✅ UVX cache refreshed (or attempted)."
else
     echo "  ⚠️ UVX command not found, skipping cache refresh."
fi

echo ""
echo "🎉 Release process for $VERSION completed successfully!"
echo "ℹ️ Remember to commit and push the updated pyproject.toml and potentially tag the release in Git."
echo "ℹ️ Restart Cursor if needed to pick up the new version."

exit 0 