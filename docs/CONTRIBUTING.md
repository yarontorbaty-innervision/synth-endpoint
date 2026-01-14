# Contributing to Innervision Synth Endpoint

This document provides guidelines for contributing to the Synth Endpoint project.

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- pnpm 8+
- Git

### Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/innervision/synth-endpoint.git
   cd synth-endpoint
   ```

2. Set up the Python analyzer:
   ```bash
   cd analyzer
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -e .
   ```

3. Set up the TypeScript generator:
   ```bash
   cd ../generator
   pnpm install
   ```

## Code Style

### Python

- Follow PEP 8 guidelines
- Use type hints for all function signatures
- Format code with Black (`black .`)
- Lint with Ruff (`ruff check .`)
- Maximum line length: 100 characters

### TypeScript

- Use strict TypeScript settings
- Format with Prettier
- Lint with ESLint
- Use explicit types where inference is not obvious

## Commit Messages

Use conventional commits format:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(analyzer): add OCR text detection to UI detector
fix(generator): correct button hover state styling
docs: update README with new CLI options
```

## Testing

### Python Tests

```bash
cd analyzer
pytest                    # Run all tests
pytest tests/test_workflow.py  # Run specific test file
pytest -v                 # Verbose output
pytest --cov             # With coverage
```

### TypeScript Tests

```bash
cd generator
pnpm test                # Run all tests
pnpm test:coverage       # With coverage
```

## Pull Request Process

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit them

3. Ensure all tests pass:
   ```bash
   # In analyzer/
   pytest
   
   # In generator/
   pnpm test
   ```

4. Push your branch and create a Pull Request

5. Request review from at least one team member

6. Address review feedback

7. Merge after approval

## Project Structure

```
synth-endpoint/
├── analyzer/           # Python video analysis
│   ├── analyzer/      # Main package
│   └── tests/         # Test suite
├── generator/         # TypeScript app generator
│   └── src/           # Source code
├── schemas/           # JSON schemas
├── examples/          # Example workflows
└── docs/              # Documentation
```

## Questions?

Reach out to the team on Slack or create a GitHub issue for discussion.
