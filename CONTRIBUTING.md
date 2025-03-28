# Contributing to Chroma MCP Server

Thank you for considering contributing to the Chroma MCP Server! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

### Reporting Bugs

- Check if the bug has already been reported in the Issues section
- Use the bug report template when creating a new issue
- Include detailed steps to reproduce the bug
- Describe what you expected to happen vs what actually happened
- Include screenshots if applicable

### Suggesting Features

- Check if the feature has already been suggested in the Issues section
- Use the feature request template when creating a new issue
- Clearly describe the feature and its benefits
- Provide examples of how the feature would be used

### Code Contributions

1. Fork the repository
2. Create a new branch for your feature or bugfix
3. Install development dependencies:

   ```bash
   pip install -e ".[dev]"
   ```

4. Make your changes
5. Add tests for your changes
6. Run tests to ensure they pass:

   ```bash
   python run_tests.py
   ```

7. Run the linters and fix any issues:

   ```bash
   black .
   isort .
   mypy .
   pylint src tests
   ```

8. Commit your changes following the conventional commits format
9. Push to your branch
10. Submit a pull request

## Development Setup

See the [README.md](README.md) for detailed setup instructions.

## Style Guidelines

This project follows:

- [PEP 8](https://www.python.org/dev/peps/pep-0008/) for code style
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) for docstrings
- Type annotations for all functions and methods
- [Conventional Commits](https://www.conventionalcommits.org/) for commit messages

## Testing

- All code contributions should include tests
- Aim for at least 80% test coverage for new code
- Both unit and integration tests are important

## Documentation

- Update the README.md if your changes affect users
- Add docstrings to all new classes and functions
- Update any relevant documentation in the docs directory

## License

By contributing to this project, you agree that your contributions will be licensed under the project's [MIT License](LICENSE.md).
