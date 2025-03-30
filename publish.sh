#!/bin/bash
# Script to publish packages to PyPI or TestPyPI
# Usage: ./publish.sh [options]
#   Options:
#     -h, --help       Show this help message
#     -y, --yes        Automatic yes to prompts (non-interactive)
#     -t, --test       Publish to TestPyPI (default)
#     -p, --prod       Publish to production PyPI
#     -v, --version    Specify version to publish (e.g. -v 0.1.1)
#     -u, --username   PyPI username (or __token__)
#     -w, --password   PyPI password or API token
#     -f, --fix-deps   Fix dependencies for TestPyPI (avoid conflicts)

# Parse command-line arguments
INTERACTIVE=true
USE_TEST_PYPI=true
VERSION=""
PYPI_USERNAME=""
PYPI_PASSWORD=""
FIX_DEPS=false

while [[ "$#" -gt 0 ]]; do
    case $1 in
        -h|--help)
            echo "Usage: ./publish.sh [options]"
            echo "  Options:"
            echo "    -h, --help       Show this help message"
            echo "    -y, --yes        Automatic yes to prompts (non-interactive)"
            echo "    -t, --test       Publish to TestPyPI (default)"
            echo "    -p, --prod       Publish to production PyPI"
            echo "    -v, --version    Specify version to publish (e.g. -v 0.1.1)"
            echo "    -u, --username   PyPI username (or __token__)"
            echo "    -w, --password   PyPI password or API token"
            echo "    -f, --fix-deps   Fix dependencies for TestPyPI (avoid conflicts)"
            echo ""
            echo "  Environment Variables:"
            echo "    PYPI_USERNAME    PyPI username (or __token__)"
            echo "    PYPI_PASSWORD    PyPI password or API token"
            echo "    PYPI_TEST_USERNAME  TestPyPI username"
            echo "    PYPI_TEST_PASSWORD  TestPyPI password or token"
            exit 0
            ;;
        -y|--yes) INTERACTIVE=false ;;
        -t|--test) USE_TEST_PYPI=true ;;
        -p|--prod) USE_TEST_PYPI=false ;;
        -v|--version) VERSION="$2"; shift ;;
        -u|--username) PYPI_USERNAME="$2"; shift ;;
        -w|--password) PYPI_PASSWORD="$2"; shift ;;
        -f|--fix-deps) FIX_DEPS=true ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Set target repository
if [ "$USE_TEST_PYPI" = true ]; then
    REPO_NAME="Test PyPI"
    REPO_ARG="-r test"
    # Check for TestPyPI credentials from environment
    if [ -z "$PYPI_USERNAME" ]; then
        PYPI_USERNAME="${PYPI_TEST_USERNAME:-$PYPI_USERNAME}"
    fi
    if [ -z "$PYPI_PASSWORD" ]; then
        PYPI_PASSWORD="${PYPI_TEST_PASSWORD:-$PYPI_PASSWORD}"
    fi
else
    REPO_NAME="PyPI"
    REPO_ARG=""
    # For production, prefer env vars specifically for production
    if [ -z "$PYPI_USERNAME" ]; then
        PYPI_USERNAME="${PYPI_USERNAME:-$PYPI_USERNAME}"
    fi
    if [ -z "$PYPI_PASSWORD" ]; then
        PYPI_PASSWORD="${PYPI_PASSWORD:-$PYPI_PASSWORD}"
    fi
fi

# Check if .pypirc exists
PYPIRC_FILE="$HOME/.pypirc"
if [ ! -f "$PYPIRC_FILE" ]; then
    echo "Warning: $PYPIRC_FILE file not found."
    echo "If you haven't configured it, you will be prompted for credentials."
    echo "See: https://packaging.python.org/en/latest/specifications/pypirc/"
    
    # Create a temporary .pypirc file if credentials are provided
    if [ ! -z "$PYPI_USERNAME" ] && [ ! -z "$PYPI_PASSWORD" ]; then
        echo "Creating temporary .pypirc file with provided credentials..."
        if [ "$USE_TEST_PYPI" = true ]; then
            # Create temp file for TestPyPI
            cat > "$PYPIRC_FILE.temp" << EOF
[distutils]
index-servers =
    test

[test]
username = $PYPI_USERNAME
password = $PYPI_PASSWORD
repository = https://test.pypi.org/legacy/
EOF
        else
            # Create temp file for PyPI
            cat > "$PYPIRC_FILE.temp" << EOF
[distutils]
index-servers =
    pypi

[pypi]
username = $PYPI_USERNAME
password = $PYPI_PASSWORD
EOF
        fi
        export PYPIRC="$PYPIRC_FILE.temp"
        echo "Temporary .pypirc created at $PYPIRC"
    fi
fi

# Install hatch if not installed
if ! command -v hatch &> /dev/null; then
    echo "Hatch not found. Installing hatch..."
    pip install hatch
fi

# Update version if specified
if [ ! -z "$VERSION" ]; then
    echo "Updating version to $VERSION..."
    # Replace version in pyproject.toml
    sed -i.bak "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml
    rm -f pyproject.toml.bak
fi

# Fix dependencies for TestPyPI if requested
if [ "$FIX_DEPS" = true ] && [ "$USE_TEST_PYPI" = true ]; then
    echo "Fixing dependencies for TestPyPI publication..."
    # Make a backup of original pyproject.toml
    cp pyproject.toml pyproject.toml.original
    
    # Much simpler approach - find the dependencies section and replace it with an empty array
    # This is more reliable than trying to parse and modify TOML
    START_LINE=$(grep -n "^dependencies = \[" pyproject.toml | cut -d: -f1)
    END_LINE=$(tail -n +$START_LINE pyproject.toml | grep -n "^]" | head -1 | cut -d: -f1)
    END_LINE=$((START_LINE + END_LINE - 1))
    
    # Check if we found both lines
    if [ ! -z "$START_LINE" ] && [ ! -z "$END_LINE" ]; then
        # Create new file with empty dependencies
        head -n $((START_LINE - 1)) pyproject.toml > pyproject.toml.new
        echo "dependencies = []  # Dependencies removed for TestPyPI publishing" >> pyproject.toml.new
        tail -n +$((END_LINE + 1)) pyproject.toml >> pyproject.toml.new
        mv pyproject.toml.new pyproject.toml
        echo "Successfully removed dependencies for TestPyPI publishing."
    else
        echo "Warning: Could not locate dependencies section in pyproject.toml"
        echo "Continuing with original file..."
    fi
    
    echo "Dependencies fixed for TestPyPI publication (all dependencies removed)."
    echo "Warning: Package on TestPyPI will have no dependencies - this is intentional."
    echo "Users will need to install required packages manually when installing from TestPyPI."
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info

# Build the package
echo "Building package with Hatch..."
hatch build

# Check if build was successful
if [ ! -d "dist" ]; then
    echo "Error: Build failed! No dist directory found."
    # Restore original pyproject.toml if modified
    if [ -f "pyproject.toml.original" ]; then
        mv pyproject.toml.original pyproject.toml
        echo "Restored original pyproject.toml."
    fi
    exit 1
fi

# Show built files
echo "Package built successfully. Files in dist directory:"
ls -la dist/
echo ""

# Confirm before publishing if in interactive mode
if [ "$INTERACTIVE" = true ]; then
    read -p "Do you want to publish these files to $REPO_NAME? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Publishing cancelled."
        # Clean up temporary pypirc file if it exists
        if [ -f "$PYPIRC_FILE.temp" ]; then
            rm -f "$PYPIRC_FILE.temp"
        fi
        # Restore original pyproject.toml if modified
        if [ -f "pyproject.toml.original" ]; then
            mv pyproject.toml.original pyproject.toml
            echo "Restored original pyproject.toml."
        fi
        exit 0
    fi
fi

# Publish the package
echo "Publishing to $REPO_NAME..."
if [ ! -z "$PYPI_USERNAME" ] && [ ! -z "$PYPI_PASSWORD" ]; then
    # Use environment variables for auth if available
    TWINE_USERNAME="$PYPI_USERNAME" TWINE_PASSWORD="$PYPI_PASSWORD" hatch publish $REPO_ARG
else
    # Otherwise use standard hatch publish which will use .pypirc or prompt
    hatch publish $REPO_ARG
fi

# Notify user of completion and clean up
STATUS=$?
# Clean up temporary pypirc file if it exists
if [ -f "$PYPIRC_FILE.temp" ]; then
    rm -f "$PYPIRC_FILE.temp"
    unset PYPIRC
fi

# Restore original pyproject.toml if it was modified
if [ -f "pyproject.toml.original" ]; then
    mv pyproject.toml.original pyproject.toml
    echo "Restored original pyproject.toml."
fi

if [ $STATUS -eq 0 ]; then
    echo "Package successfully published to $REPO_NAME!"
    
    if [ "$USE_TEST_PYPI" = true ]; then
        echo ""
        echo "Note: The package was published to TestPyPI without dependencies."
        echo "To test installation, you need to specify additional dependencies manually:"
        echo ""
        echo "pip install --index-url https://test.pypi.org/simple/ \\"
        echo "    --extra-index-url https://pypi.org/simple/ \\"
        echo "    chroma-mcp-server==$VERSION \\"
        echo "    chromadb fastapi uvicorn python-dotenv pydantic"
        echo ""
    fi
    
    echo "To verify installation from a wheel file, run:"
    echo "./test_uvx_install.sh"
else
    echo "Error publishing to $REPO_NAME. Check the output above for details."
    exit 1
fi 