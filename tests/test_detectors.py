"""
Tests for photo detection modules.
"""

import pytest
import numpy as np
import cv2
import tempfile
import os
from pathlib import Path

from phaicull.detectors import (
    BlurDetector,
    ExposureDetector,
    ResolutionDetector,
    NoiseDetector,
    DuplicateDetector,
    FaceDetector
)


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


class TestBlurDetector:
    """Tests for BlurDetector."""
    
    def test_sharp_image_not_blurred(self, temp_dir):
        """Test that a sharp image is not detected as blurred."""
        img_path = os.path.join(temp_dir, "sharp.jpg")
        img = np.ones((600, 800, 3), dtype=np.uint8) * 128
        # Add sharp features
        cv2.rectangle(img, (100, 100), (700, 500), (255, 255, 255), 2)
        cv2.imwrite(img_path, img)
        
        detector = BlurDetector(threshold=100.0)
        is_blurred, score = detector.is_blurred(img_path)
        
        assert not is_blurred, "Sharp image should not be detected as blurred"
        assert score > 100.0, "Sharp image should have high variance score"
    
    def test_blurred_image_detected(self, temp_dir):
        """Test that a blurred image is detected."""
        img_path = os.path.join(temp_dir, "blurred.jpg")
        img = np.ones((600, 800, 3), dtype=np.uint8) * 128
        cv2.rectangle(img, (100, 100), (700, 500), (255, 255, 255), 2)
        blurred = cv2.GaussianBlur(img, (51, 51), 0)
        cv2.imwrite(img_path, blurred)
        
        detector = BlurDetector(threshold=100.0)
        is_blurred, score = detector.is_blurred(img_path)
        
        assert is_blurred, "Blurred image should be detected"
        assert score < 100.0, "Blurred image should have low variance score"


class TestExposureDetector:
    """Tests for ExposureDetector."""
    
    def test_normal_exposure(self, temp_dir):
        """Test that normal exposure is not flagged."""
        img_path = create_test_image(os.path.join(temp_dir, "normal.jpg"), color=128)
        
        detector = ExposureDetector()
        is_dark, is_overexposed, stats = detector.analyze_exposure(img_path)
        
        assert not is_dark, "Normal image should not be dark"
        assert not is_overexposed, "Normal image should not be overexposed"
    
    def test_dark_image_detected(self, temp_dir):
        """Test that dark images are detected."""
        img_path = create_test_image(os.path.join(temp_dir, "dark.jpg"), color=20)
        
        detector = ExposureDetector()
        is_dark, is_overexposed, stats = detector.analyze_exposure(img_path)
        
        assert is_dark, "Dark image should be detected"
        assert not is_overexposed, "Dark image should not be overexposed"
    
    def test_overexposed_image_detected(self, temp_dir):
        """Test that overexposed images are detected."""
        img_path = create_test_image(os.path.join(temp_dir, "bright.jpg"), color=240)
        
        detector = ExposureDetector()
        is_dark, is_overexposed, stats = detector.analyze_exposure(img_path)
        
        assert not is_dark, "Overexposed image should not be dark"
        assert is_overexposed, "Overexposed image should be detected"


class TestResolutionDetector:
    """Tests for ResolutionDetector."""
    
    def test_normal_resolution(self, temp_dir):
        """Test that normal resolution is not flagged."""
        img_path = create_test_image(os.path.join(temp_dir, "normal.jpg"), size=(1920, 1080))
        
        detector = ResolutionDetector(min_width=800, min_height=600)
        is_low_res, info = detector.is_low_resolution(img_path)
        
        assert not is_low_res, "High resolution image should not be flagged"
        assert info['width'] == 1920
        assert info['height'] == 1080
    
    def test_low_resolution_detected(self, temp_dir):
        """Test that low resolution is detected."""
        img_path = create_test_image(os.path.join(temp_dir, "small.jpg"), size=(640, 480))
        
        detector = ResolutionDetector(min_width=800, min_height=600)
        is_low_res, info = detector.is_low_resolution(img_path)
        
        assert is_low_res, "Low resolution image should be detected"
        assert info['width'] == 640
        assert info['height'] == 480


class TestDuplicateDetector:
    """Tests for DuplicateDetector."""
    
    def test_identical_images_are_duplicates(self, temp_dir):
        """Test that identical images are detected as duplicates."""
        img1_path = create_test_image(os.path.join(temp_dir, "img1.jpg"))
        img2_path = create_test_image(os.path.join(temp_dir, "img2.jpg"))
        
        detector = DuplicateDetector()
        are_similar, distance = detector.are_similar(img1_path, img2_path)
        
        assert are_similar, "Identical images should be detected as duplicates"
        assert distance == 0, "Identical images should have zero distance"
    
    def test_different_images_not_duplicates(self, temp_dir):
        """Test that different images are not detected as duplicates."""
        # Create truly different images with distinct patterns
        img1_path = os.path.join(temp_dir, "img1.jpg")
        img1 = np.ones((600, 800, 3), dtype=np.uint8) * 50
        cv2.rectangle(img1, (100, 100), (300, 300), (255, 255, 255), -1)
        cv2.imwrite(img1_path, img1)
        
        img2_path = os.path.join(temp_dir, "img2.jpg")
        img2 = np.ones((600, 800, 3), dtype=np.uint8) * 200
        cv2.circle(img2, (400, 300), 100, (0, 0, 0), -1)
        cv2.imwrite(img2_path, img2)
        
        detector = DuplicateDetector(similarity_threshold=5)
        are_similar, distance = detector.are_similar(img1_path, img2_path)
        
        assert not are_similar, "Different images should not be duplicates"
        assert distance > 5, "Different images should have high distance"


class TestFaceDetector:
    """Tests for FaceDetector."""
    
    def test_no_faces_in_blank_image(self, temp_dir):
        """Test that blank images have no faces."""
        img_path = create_test_image(os.path.join(temp_dir, "blank.jpg"))
        
        detector = FaceDetector()
        has_people, num_faces = detector.has_people(img_path)
        
        assert not has_people, "Blank image should have no faces"
        assert num_faces == 0, "Blank image should have zero faces"
