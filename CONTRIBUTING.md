# Contributing to omniray

Thank you for your interest in contributing to omniwrap!

## Development Setup

```bash
git clone https://github.com/omniviser/omniray.git
cd omniray

# Install all packages in development mode
uv sync

# Install pre-commit hooks
pre-commit install
```

## Running Tests

```bash
# omniwrap core tests
cd packages/omniwrap
uv run pytest tests/ -v --cov=omniwrap --cov-fail-under=100

# omniray tests
cd packages/omniray
uv run pytest tests/ -v --cov=omniray --cov-fail-under=100
```

## Code Style

Pre-commit hooks run automatically on each commit. To run manually:

```bash
ruff check packages/
ruff format packages/
mypy packages/omniwrap/omniwrap/
mypy packages/omniray/omniray/
```

- **Linter/Formatter**: Ruff (ALL rules enabled)
- **Type checker**: MyPy (strict)
- **Line length**: 100 characters
- **Docstrings**: Google style
- **Mocking**: Use `pytest-mock`'s `mocker` fixture, not `unittest.mock`

## Pull Request Process

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes
4. Ensure all tests pass with 100% coverage
5. Ensure pre-commit hooks pass
6. Submit a pull request

## Reporting Issues

Use [GitHub Issues](https://github.com/omniviser/omniray/issues) to report bugs or request features.

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
