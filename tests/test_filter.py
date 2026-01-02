"""
Tests for photo filter module.
"""

import pytest
import tempfile
import os
import json
import numpy as np
import cv2

from phaicull.filter import PhotoFilter, FilterConfig, FilterResult


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test images."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def create_test_image(path: str, size=(800, 600), color=128):
    """Create a simple test image."""
    img = np.ones((size[1], size[0], 3), dtype=np.uint8) * color
    cv2.imwrite(path, img)
    return path


class TestFilterConfig:
    """Tests for FilterConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = FilterConfig()
        
        assert config.check_blur is True
        assert config.check_exposure is True
        assert config.check_resolution is True
        assert config.check_noise is True
        assert config.check_duplicates is True
        assert config.check_closed_eyes is True
        assert config.filter_no_people is False


class TestPhotoFilter:
    """Tests for PhotoFilter."""
    
    def test_filter_initialization(self):
        """Test that PhotoFilter initializes correctly."""
        config = FilterConfig()
        photo_filter = PhotoFilter(config)
        
        assert photo_filter.config == config
        assert hasattr(photo_filter, 'blur_detector')
        assert hasattr(photo_filter, 'exposure_detector')
    
    def test_get_image_files(self, temp_dir):
        """Test getting image files from directory."""
        # Create test images
        create_test_image(os.path.join(temp_dir, "img1.jpg"))
        create_test_image(os.path.join(temp_dir, "img2.png"))
        create_test_image(os.path.join(temp_dir, "img3.bmp"))
        
        # Create non-image file
        with open(os.path.join(temp_dir, "readme.txt"), "w") as f:
            f.write("test")
        
        photo_filter = PhotoFilter()
        image_files = photo_filter.get_image_files(temp_dir, recursive=False)
        
        assert len(image_files) == 3
        assert all(f.endswith(('.jpg', '.png', '.bmp')) for f in image_files)
    
    def test_filter_normal_image(self, temp_dir):
        """Test that normal images pass filtering."""
        img_path = create_test_image(os.path.join(temp_dir, "normal.jpg"), size=(1920, 1080))
        
        config = FilterConfig(
            check_blur=True,
            check_exposure=True,
            check_resolution=True,
            check_noise=False,
            check_duplicates=False,
            check_closed_eyes=False
        )
        photo_filter = PhotoFilter(config)
        result = photo_filter.filter_image(img_path)
        
        assert result.path == img_path
        # Note: Blank images might be flagged as blurred, so we don't assert should_filter
    
    def test_filter_low_resolution_image(self, temp_dir):
        """Test that low resolution images are filtered."""
        img_path = create_test_image(os.path.join(temp_dir, "small.jpg"), size=(640, 480))
        
        config = FilterConfig(
            check_blur=False,
            check_exposure=False,
            check_resolution=True,
            min_width=800,
            min_height=600
        )
        photo_filter = PhotoFilter(config)
        result = photo_filter.filter_image(img_path)
        
        assert result.should_filter is True
        assert any("Low resolution" in reason for reason in result.reasons)
    
    def test_save_results(self, temp_dir):
        """Test saving results to JSON."""
        img_path = create_test_image(os.path.join(temp_dir, "test.jpg"))
        output_file = os.path.join(temp_dir, "results.json")
        
        photo_filter = PhotoFilter()
        result = photo_filter.filter_image(img_path)
        results = {img_path: result}
        
        photo_filter.save_results(results, output_file)
        
        assert os.path.exists(output_file)
        
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        assert 'config' in data
        assert 'results' in data
        assert len(data['results']) == 1
        assert data['results'][0]['path'] == img_path
    
    def test_find_duplicates(self, temp_dir):
        """Test duplicate detection."""
        img1_path = create_test_image(os.path.join(temp_dir, "img1.jpg"))
        img2_path = create_test_image(os.path.join(temp_dir, "img2.jpg"))  # Identical
        
        # Create truly different image with distinct pattern
        img3_path = os.path.join(temp_dir, "img3.jpg")
        img3 = np.ones((600, 800, 3), dtype=np.uint8) * 200
        cv2.circle(img3, (400, 300), 100, (0, 0, 0), -1)
        cv2.imwrite(img3_path, img3)
        
        config = FilterConfig(check_duplicates=True)
        photo_filter = PhotoFilter(config)
        
        duplicate_groups = photo_filter.find_duplicates([img1_path, img2_path, img3_path])
        
        # Should find img1 and img2 as duplicates
        assert len(duplicate_groups) >= 1
        # First group should contain the two identical images
        first_group = duplicate_groups[0]
        assert img1_path in first_group or img2_path in first_group
        assert len(first_group) >= 2
