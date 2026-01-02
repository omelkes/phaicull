# Installation Guide

## Requirements

- Python 3.8 or higher
- pip (Python package manager)

## Installation Methods

### Method 1: From Source (Recommended for Development)

1. Clone the repository:
```bash
git clone https://github.com/omelkes/phaicull.git
cd phaicull
```

2. Install in editable mode:
```bash
pip install -e .
```

3. Verify installation:
```bash
phaicull --version
```

### Method 2: Direct Install from GitHub

```bash
pip install git+https://github.com/omelkes/phaicull.git
```

### Method 3: From PyPI (when published)

```bash
pip install phaicull
```

## Dependencies

The following packages will be automatically installed:

- **numpy** (>=1.21.0) - Numerical operations
- **opencv-python** (>=4.5.0) - Computer vision and image processing
- **Pillow** (>=9.0.0) - Image file handling
- **imagehash** (>=4.3.0) - Perceptual hashing for duplicate detection
- **tqdm** (>=4.62.0) - Progress bars

## Development Installation

If you want to contribute to the project or run tests:

1. Install with development dependencies:
```bash
pip install -e ".[dev]"
```

2. Run tests:
```bash
pytest tests/
```

3. Run tests with coverage:
```bash
pytest tests/ --cov=phaicull --cov-report=html
```

## Platform-Specific Notes

### Linux

Most distributions work out of the box. If you encounter issues with OpenCV, you may need to install system libraries:

```bash
# Ubuntu/Debian
sudo apt-get install python3-opencv libopencv-dev

# Fedora/RHEL
sudo dnf install opencv python3-opencv
```

### macOS

OpenCV should work without additional setup. If you encounter issues:

```bash
brew install opencv
```

### Windows

The wheel packages should work out of the box. If you encounter issues:

1. Install Visual C++ Redistributable
2. Use the `opencv-python` package (which should install automatically)

## Troubleshooting

### ImportError: No module named 'cv2'

Try reinstalling opencv-python:
```bash
pip uninstall opencv-python opencv-contrib-python opencv-python-headless
pip install opencv-python
```

### Permission Errors

If you don't have admin/sudo access, install for your user:
```bash
pip install --user -e .
```

### Virtual Environments (Recommended)

Using a virtual environment prevents conflicts with other Python packages:

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install phaicull
pip install -e .
```

## Verifying Installation

Run a quick test:

```bash
# Check version
phaicull --version

# See help
phaicull --help
```

## Updating

If installed from source:
```bash
cd phaicull
git pull
pip install -e . --upgrade
```

If installed from PyPI:
```bash
pip install --upgrade phaicull
```
