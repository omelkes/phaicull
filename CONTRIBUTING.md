# Contributing to phaicull

Thank you for considering contributing to phaicull! This document provides guidelines for contributing to the project.

## Ways to Contribute

- **Report bugs**: Open an issue describing the bug and how to reproduce it
- **Suggest features**: Open an issue describing the feature and its use case
- **Improve documentation**: Fix typos, clarify explanations, add examples
- **Write code**: Fix bugs, implement features, optimize performance
- **Write tests**: Add test coverage for existing or new functionality

## Development Setup

1. Fork the repository on GitHub

2. Clone your fork:
```bash
git clone https://github.com/YOUR_USERNAME/phaicull.git
cd phaicull
```

3. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

4. Install in development mode:
```bash
pip install -e ".[dev]"
```

5. Create a new branch:
```bash
git checkout -b feature/your-feature-name
```

## Code Style

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Write docstrings for all public functions and classes
- Keep functions focused and modular
- Maximum line length: 100 characters

### Running Code Formatters

```bash
# Format code with black
black phaicull tests

# Check with flake8
flake8 phaicull tests
```

## Testing

All changes should include appropriate tests.

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=phaicull --cov-report=html

# Run specific test file
pytest tests/test_detectors.py

# Run specific test
pytest tests/test_detectors.py::TestBlurDetector::test_sharp_image_not_blurred
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files `test_*.py`
- Name test classes `Test*`
- Name test functions `test_*`
- Use descriptive test names that explain what is being tested
- Each test should test one specific behavior
- Use fixtures for common setup

Example:
```python
def test_blur_detection_on_sharp_image(self, temp_dir):
    """Test that sharp images are not flagged as blurred."""
    # Setup
    img_path = create_sharp_image(temp_dir)
    detector = BlurDetector(threshold=100.0)
    
    # Execute
    is_blurred, score = detector.is_blurred(img_path)
    
    # Assert
    assert not is_blurred
    assert score > 100.0
```

## Pull Request Process

1. **Update your branch** with the latest main:
```bash
git checkout main
git pull upstream main
git checkout your-feature-branch
git rebase main
```

2. **Run tests** and ensure they pass:
```bash
pytest tests/
```

3. **Update documentation** if needed:
   - Update README.md for user-facing changes
   - Update docstrings for API changes
   - Add examples if appropriate

4. **Commit your changes**:
   - Use clear, descriptive commit messages
   - Reference issue numbers if applicable
   - One logical change per commit

Example commit message:
```
Add noise threshold parameter to NoiseDetector

- Add configurable threshold parameter
- Update tests to cover new parameter
- Update documentation

Fixes #42
```

5. **Push to your fork**:
```bash
git push origin your-feature-branch
```

6. **Open a Pull Request**:
   - Provide a clear description of the changes
   - Reference any related issues
   - Include screenshots for UI changes
   - Explain the motivation for the change

7. **Respond to feedback**:
   - Address review comments
   - Update the PR as needed
   - Be respectful and constructive

## Code Review Guidelines

When reviewing pull requests:

- Be constructive and respectful
- Explain the reasoning behind suggestions
- Distinguish between required changes and suggestions
- Approve when ready, even if minor suggestions remain

## Project Structure

```
phaicull/
├── phaicull/           # Main package
│   ├── __init__.py     # Package initialization
│   ├── cli.py          # Command-line interface
│   ├── detectors.py    # Detection modules
│   └── filter.py       # Main filtering logic
├── tests/              # Test suite
│   ├── test_detectors.py
│   └── test_filter.py
├── README.md           # Main documentation
├── INSTALL.md          # Installation guide
├── EXAMPLES.md         # Usage examples
├── pyproject.toml      # Project configuration
└── LICENSE             # MIT License
```

## Adding New Detectors

To add a new detection module:

1. Add the detector class to `phaicull/detectors.py`:
```python
class NewDetector:
    """Detect some image quality issue."""
    
    def __init__(self, threshold: float = 100.0):
        self.threshold = threshold
    
    def detect_issue(self, image_path: str) -> Tuple[bool, float]:
        """Detect the issue in an image."""
        # Implementation
        pass
```

2. Integrate it into `PhotoFilter` in `phaicull/filter.py`

3. Add configuration options to `FilterConfig`

4. Add CLI arguments in `phaicull/cli.py`

5. Write tests in `tests/test_detectors.py`

6. Update documentation

## Performance Considerations

- Process images efficiently (avoid reading the same image multiple times)
- Use numpy operations when possible
- Consider memory usage for large photo collections
- Profile code before optimizing

## Reporting Issues

When reporting bugs, include:

- phaicull version (`phaicull --version`)
- Python version
- Operating system
- Steps to reproduce
- Expected behavior
- Actual behavior
- Error messages (full traceback if applicable)
- Sample images (if relevant and not sensitive)

## Feature Requests

When requesting features, describe:

- The use case and problem it solves
- Proposed solution or approach
- Any alternatives you've considered
- Examples of similar features in other tools

## Questions?

- Open an issue with the "question" label
- Check existing issues and documentation first

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on what is best for the community
- Show empathy towards other community members

Thank you for contributing to phaicull!
