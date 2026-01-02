"""
Image quality detection modules for identifying various photo issues.
"""

import cv2
import numpy as np
from typing import Tuple, Optional
import imagehash
from PIL import Image


class BlurDetector:
    """Detect blurred images using Laplacian variance."""
    
    def __init__(self, threshold: float = 100.0):
        """
        Initialize blur detector.
        
        Args:
            threshold: Laplacian variance threshold. Images below this are considered blurred.
        """
        self.threshold = threshold
    
    def is_blurred(self, image_path: str) -> Tuple[bool, float]:
        """
        Check if an image is blurred.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            Tuple of (is_blurred, blur_score) where lower scores indicate more blur.
        """
        img = cv2.imread(image_path)
        if img is None:
            return False, 0.0
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        return laplacian_var < self.threshold, laplacian_var


class ExposureDetector:
    """Detect dark or overexposed images using histogram analysis."""
    
    def __init__(self, dark_threshold: float = 0.5, bright_threshold: float = 0.5):
        """
        Initialize exposure detector.
        
        Args:
            dark_threshold: Fraction of pixels that must be very dark (< 50) to flag as dark.
            bright_threshold: Fraction of pixels that must be very bright (> 205) to flag as overexposed.
        """
        self.dark_threshold = dark_threshold
        self.bright_threshold = bright_threshold
    
    def analyze_exposure(self, image_path: str) -> Tuple[bool, bool, dict]:
        """
        Analyze image exposure.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            Tuple of (is_too_dark, is_overexposed, stats_dict).
        """
        img = cv2.imread(image_path)
        if img is None:
            return False, False, {}
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Calculate histogram statistics
        total_pixels = gray.shape[0] * gray.shape[1]
        dark_pixels = np.sum(gray < 50)
        bright_pixels = np.sum(gray > 205)
        
        dark_ratio = dark_pixels / total_pixels
        bright_ratio = bright_pixels / total_pixels
        
        mean_brightness = np.mean(gray)
        
        stats = {
            'mean_brightness': float(mean_brightness),
            'dark_ratio': float(dark_ratio),
            'bright_ratio': float(bright_ratio)
        }
        
        is_dark = dark_ratio > self.dark_threshold
        is_overexposed = bright_ratio > self.bright_threshold
        
        return is_dark, is_overexposed, stats


class ResolutionDetector:
    """Detect low-resolution images."""
    
    def __init__(self, min_width: int = 800, min_height: int = 600):
        """
        Initialize resolution detector.
        
        Args:
            min_width: Minimum acceptable width in pixels.
            min_height: Minimum acceptable height in pixels.
        """
        self.min_width = min_width
        self.min_height = min_height
    
    def is_low_resolution(self, image_path: str) -> Tuple[bool, dict]:
        """
        Check if image has low resolution.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            Tuple of (is_low_res, resolution_dict).
        """
        img = cv2.imread(image_path)
        if img is None:
            return False, {}
        
        height, width = img.shape[:2]
        
        resolution_info = {
            'width': width,
            'height': height,
            'total_pixels': width * height
        }
        
        is_low_res = width < self.min_width or height < self.min_height
        
        return is_low_res, resolution_info


class NoiseDetector:
    """Detect noisy images using edge detection and variance analysis."""
    
    def __init__(self, noise_threshold: float = 1000.0):
        """
        Initialize noise detector.
        
        Args:
            noise_threshold: Threshold for noise metric. Higher values indicate more noise.
        """
        self.noise_threshold = noise_threshold
    
    def is_noisy(self, image_path: str) -> Tuple[bool, float]:
        """
        Check if an image is noisy.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            Tuple of (is_noisy, noise_score).
        """
        img = cv2.imread(image_path)
        if img is None:
            return False, 0.0
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Use bilateral filter to estimate noise
        smoothed = cv2.bilateralFilter(gray, 9, 75, 75)
        noise = cv2.absdiff(gray, smoothed)
        noise_score = float(np.mean(noise))
        
        return noise_score > self.noise_threshold, noise_score


class DuplicateDetector:
    """Detect duplicate and near-duplicate images using perceptual hashing."""
    
    def __init__(self, hash_size: int = 8, similarity_threshold: int = 5):
        """
        Initialize duplicate detector.
        
        Args:
            hash_size: Size of the hash (larger = more precise).
            similarity_threshold: Maximum hamming distance to consider images as duplicates.
        """
        self.hash_size = hash_size
        self.similarity_threshold = similarity_threshold
        self.hash_cache = {}
    
    def compute_hash(self, image_path: str) -> Optional[imagehash.ImageHash]:
        """
        Compute perceptual hash for an image.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            ImageHash object or None if image cannot be loaded.
        """
        if image_path in self.hash_cache:
            return self.hash_cache[image_path]
        
        try:
            img = Image.open(image_path)
            img_hash = imagehash.average_hash(img, hash_size=self.hash_size)
            self.hash_cache[image_path] = img_hash
            return img_hash
        except Exception:
            return None
    
    def are_similar(self, image_path1: str, image_path2: str) -> Tuple[bool, int]:
        """
        Check if two images are similar.
        
        Args:
            image_path1: Path to first image.
            image_path2: Path to second image.
            
        Returns:
            Tuple of (are_similar, hamming_distance).
        """
        hash1 = self.compute_hash(image_path1)
        hash2 = self.compute_hash(image_path2)
        
        if hash1 is None or hash2 is None:
            return False, -1
        
        distance = hash1 - hash2
        return distance <= self.similarity_threshold, distance
    
    def find_duplicates(self, image_paths: list) -> list:
        """
        Find groups of duplicate images.
        
        Args:
            image_paths: List of image file paths.
            
        Returns:
            List of duplicate groups, where each group is a list of similar image paths.
        """
        # Compute all hashes first
        hashes = {}
        for path in image_paths:
            img_hash = self.compute_hash(path)
            if img_hash is not None:
                hashes[path] = img_hash
        
        # Find duplicates
        processed = set()
        duplicate_groups = []
        
        paths = list(hashes.keys())
        for i, path1 in enumerate(paths):
            if path1 in processed:
                continue
            
            group = [path1]
            for path2 in paths[i+1:]:
                if path2 in processed:
                    continue
                
                distance = hashes[path1] - hashes[path2]
                if distance <= self.similarity_threshold:
                    group.append(path2)
                    processed.add(path2)
            
            if len(group) > 1:
                duplicate_groups.append(group)
                processed.add(path1)
        
        return duplicate_groups


class FaceDetector:
    """Detect faces and analyze face features like closed eyes."""
    
    def __init__(self):
        """Initialize face detector with OpenCV cascade classifiers."""
        # Load pre-trained cascade classifiers
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
    
    def has_people(self, image_path: str) -> Tuple[bool, int]:
        """
        Check if image contains people.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            Tuple of (has_people, number_of_faces).
        """
        img = cv2.imread(image_path)
        if img is None:
            return False, 0
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        
        num_faces = len(faces)
        return num_faces > 0, num_faces
    
    def detect_closed_eyes(self, image_path: str) -> Tuple[bool, dict]:
        """
        Detect if people in the image have closed eyes.
        
        Note: This is a basic detection using Haar Cascades. A face without detected
        eyes could indicate closed eyes, but could also be due to poor lighting, 
        profile angle, or detection failure. This method provides a best-effort
        heuristic and may have false positives.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            Tuple of (has_closed_eyes, detection_info).
        """
        img = cv2.imread(image_path)
        if img is None:
            return False, {}
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        
        info = {
            'num_faces': len(faces),
            'faces_with_eyes_detected': 0,
            'faces_without_eyes': 0
        }
        
        if len(faces) == 0:
            return False, info
        
        # For each face, try to detect eyes
        for (x, y, w, h) in faces:
            roi_gray = gray[y:y+h, x:x+w]
            eyes = self.eye_cascade.detectMultiScale(roi_gray, 1.1, 5)
            
            if len(eyes) >= 1:
                info['faces_with_eyes_detected'] += 1
            else:
                info['faces_without_eyes'] += 1
        
        # Consider closed eyes if we detect faces but no eyes
        # Note: This is a heuristic and may have false positives in challenging conditions
        has_closed_eyes = info['faces_without_eyes'] > 0 and info['num_faces'] > 0
        
        return has_closed_eyes, info
