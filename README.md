# phaicull

AI-powered photo culling tool - Quickly filter out blurred, dark, duplicate, and low-quality photos

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

**phaicull** is a free, open-source tool designed to help users (especially parents with thousands of family photos) quickly filter out unwanted images. It uses computer vision and image processing to detect:

- 📷 **Blurred photos** - Using Laplacian variance detection
- 🌑 **Dark or overexposed photos** - Using histogram analysis
- 👯 **Duplicates and near-duplicates** - Using perceptual hashing
- 😴 **Photos with people with closed eyes** - Using face and eye detection
- 👤 **Photos without people** (optional) - Using face detection
- 📉 **Low-resolution or noisy photos** - Using resolution and noise analysis

The goal is **speed, simplicity, and accuracy**, not full Photoshop-level editing.

## Features

- **Fast Processing**: Efficiently processes large photo collections
- **Configurable Filters**: Enable/disable specific checks and adjust thresholds
- **Multiple Actions**: Generate reports, copy or move filtered photos
- **Preserves Structure**: Maintains directory structure when organizing photos
- **JSON Reports**: Detailed analysis results in JSON format
- **Command-line Interface**: Simple and powerful CLI

## Installation

### From Source

```bash
git clone https://github.com/omelkes/phaicull.git
cd phaicull
pip install -e .
```

### Using pip (when published)

```bash
pip install phaicull
```

### Requirements

- Python 3.8 or higher
- OpenCV (automatically installed)
- Pillow (automatically installed)
- numpy (automatically installed)

## Quick Start

### Basic Usage

Analyze photos in a directory:

```bash
phaicull /path/to/photos
```

This will:
1. Scan all images in the directory
2. Analyze each photo for quality issues
3. Generate a report (`filter_report.json`)
4. Display summary statistics

### Move Filtered Photos

Separate good photos from bad ones:

```bash
phaicull /path/to/photos --action move --output /path/to/good_photos
```

This moves all high-quality photos to the output directory, leaving filtered photos in the original location.

### Copy Filtered Photos to Review

Copy photos flagged for filtering to review them manually:

```bash
phaicull /path/to/photos --action copy --output /path/to/review --keep-filtered
```

## Usage Examples

### Filter Only Blurred and Duplicate Photos

```bash
phaicull /path/to/photos --no-exposure --no-resolution --no-noise --no-closed-eyes
```

### Adjust Blur Sensitivity

```bash
# More strict (filter more photos)
phaicull /path/to/photos --blur-threshold 150

# Less strict (filter fewer photos)
phaicull /path/to/photos --blur-threshold 50
```

### Filter Photos Without People

```bash
phaicull /path/to/photos --filter-no-people
```

### Set Minimum Resolution

```bash
phaicull /path/to/photos --min-width 1920 --min-height 1080
```

### Process Single Directory (No Subdirectories)

```bash
phaicull /path/to/photos --no-recursive
```

## Command-Line Options

### Actions

- `--action report` - Only generate a report (default)
- `--action copy` - Copy photos to output directory
- `--action move` - Move photos to output directory
- `--keep-filtered` - Keep filtered photos instead of good ones (with copy/move)

### Filter Toggles

- `--no-blur` - Disable blur detection
- `--no-exposure` - Disable exposure detection
- `--no-resolution` - Disable resolution detection
- `--no-noise` - Disable noise detection
- `--no-duplicates` - Disable duplicate detection
- `--no-closed-eyes` - Disable closed eyes detection
- `--filter-no-people` - Filter photos without people

### Filter Parameters

- `--blur-threshold` - Blur detection threshold (default: 100.0, lower = more strict)
- `--dark-threshold` - Dark photo threshold 0-1 (default: 0.5)
- `--bright-threshold` - Overexposed threshold 0-1 (default: 0.5)
- `--min-width` - Minimum width in pixels (default: 800)
- `--min-height` - Minimum height in pixels (default: 600)
- `--noise-threshold` - Noise detection threshold (default: 1000.0)
- `--duplicate-similarity` - Hamming distance for duplicates 0-64 (default: 5)

### Output Options

- `--output` - Output directory for copy/move actions
- `--report` - Path to JSON report file (default: filter_report.json)
- `--no-recursive` - Don't scan subdirectories

## Understanding the Report

The JSON report contains detailed information about each image:

```json
{
  "config": {
    "check_blur": true,
    "blur_threshold": 100.0,
    ...
  },
  "results": [
    {
      "path": "/path/to/photo.jpg",
      "should_filter": true,
      "reasons": ["Blurred (score: 45.32)", "Too dark"],
      "details": {
        "blur_score": 45.32,
        "exposure_stats": {
          "mean_brightness": 35.2,
          "dark_ratio": 0.65
        },
        ...
      }
    }
  ]
}
```

## How It Works

### Blur Detection

Uses the Laplacian operator to calculate image sharpness. Blurred images have low variance in the Laplacian.

### Exposure Detection

Analyzes pixel intensity histograms to detect:
- **Dark photos**: High proportion of very dark pixels
- **Overexposed photos**: High proportion of very bright pixels

### Duplicate Detection

Uses perceptual hashing (average hash) to find visually similar images. Compares hash values using Hamming distance.

### Closed Eyes Detection

1. Detects faces using Haar Cascade classifiers
2. For each face, attempts to detect open eyes
3. Flags photos where faces are found but eyes are not detected

### Resolution & Noise Detection

- **Resolution**: Checks if image dimensions meet minimum requirements
- **Noise**: Compares original image with bilateral-filtered version to estimate noise level

## Limitations

- **Closed eyes detection**: Uses basic Haar Cascades, which may have false positives/negatives. Works best with frontal faces and good lighting.
- **Face detection**: May not detect faces in profile, with poor lighting, or at extreme angles.
- **Blur detection**: Works best for general blur; may not catch motion blur in specific regions.
- **Performance**: Processing large collections can take time, especially with all checks enabled.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenCV for computer vision capabilities
- imagehash for perceptual hashing
- The open-source community for various image processing algorithms

## Support

If you find this tool helpful, please star the repository! For issues or questions, please open an issue on GitHub.
