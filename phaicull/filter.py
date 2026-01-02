"""
Photo filtering engine that orchestrates all quality checks.
"""

import os
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from pathlib import Path
import json

from .detectors import (
    BlurDetector,
    ExposureDetector,
    ResolutionDetector,
    NoiseDetector,
    DuplicateDetector,
    FaceDetector
)


@dataclass
class FilterConfig:
    """Configuration for photo filtering."""
    check_blur: bool = True
    blur_threshold: float = 100.0
    
    check_exposure: bool = True
    dark_threshold: float = 0.5
    bright_threshold: float = 0.5
    
    check_resolution: bool = True
    min_width: int = 800
    min_height: int = 600
    
    check_noise: bool = True
    noise_threshold: float = 1000.0
    
    check_duplicates: bool = True
    duplicate_similarity: int = 5
    
    check_closed_eyes: bool = True
    
    filter_no_people: bool = False
    
    supported_extensions: Set[str] = field(default_factory=lambda: {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'})


@dataclass
class FilterResult:
    """Result of filtering a single photo."""
    path: str
    should_filter: bool
    reasons: List[str] = field(default_factory=list)
    details: Dict = field(default_factory=dict)


class PhotoFilter:
    """Main photo filtering engine."""
    
    def __init__(self, config: Optional[FilterConfig] = None):
        """
        Initialize photo filter with configuration.
        
        Args:
            config: FilterConfig object. If None, uses default configuration.
        """
        self.config = config or FilterConfig()
        
        # Initialize detectors based on config
        if self.config.check_blur:
            self.blur_detector = BlurDetector(threshold=self.config.blur_threshold)
        
        if self.config.check_exposure:
            self.exposure_detector = ExposureDetector(
                dark_threshold=self.config.dark_threshold,
                bright_threshold=self.config.bright_threshold
            )
        
        if self.config.check_resolution:
            self.resolution_detector = ResolutionDetector(
                min_width=self.config.min_width,
                min_height=self.config.min_height
            )
        
        if self.config.check_noise:
            self.noise_detector = NoiseDetector(noise_threshold=self.config.noise_threshold)
        
        if self.config.check_duplicates:
            self.duplicate_detector = DuplicateDetector(
                similarity_threshold=self.config.duplicate_similarity
            )
        
        if self.config.check_closed_eyes or self.config.filter_no_people:
            self.face_detector = FaceDetector()
    
    def filter_image(self, image_path: str) -> FilterResult:
        """
        Filter a single image and return the result.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            FilterResult object with filtering decision and details.
        """
        result = FilterResult(path=image_path, should_filter=False)
        
        # Check blur
        if self.config.check_blur:
            is_blurred, blur_score = self.blur_detector.is_blurred(image_path)
            result.details['blur_score'] = blur_score
            if is_blurred:
                result.should_filter = True
                result.reasons.append(f"Blurred (score: {blur_score:.2f})")
        
        # Check exposure
        if self.config.check_exposure:
            is_dark, is_overexposed, stats = self.exposure_detector.analyze_exposure(image_path)
            result.details['exposure_stats'] = stats
            if is_dark:
                result.should_filter = True
                result.reasons.append("Too dark")
            if is_overexposed:
                result.should_filter = True
                result.reasons.append("Overexposed")
        
        # Check resolution
        if self.config.check_resolution:
            is_low_res, res_info = self.resolution_detector.is_low_resolution(image_path)
            result.details['resolution'] = res_info
            if is_low_res:
                result.should_filter = True
                result.reasons.append(
                    f"Low resolution ({res_info.get('width', 0)}x{res_info.get('height', 0)})"
                )
        
        # Check noise
        if self.config.check_noise:
            is_noisy, noise_score = self.noise_detector.is_noisy(image_path)
            result.details['noise_score'] = noise_score
            if is_noisy:
                result.should_filter = True
                result.reasons.append(f"Noisy (score: {noise_score:.2f})")
        
        # Check for people and closed eyes
        if self.config.filter_no_people or self.config.check_closed_eyes:
            has_people, num_faces = self.face_detector.has_people(image_path)
            result.details['num_faces'] = num_faces
            
            if self.config.filter_no_people and not has_people:
                result.should_filter = True
                result.reasons.append("No people detected")
            
            if self.config.check_closed_eyes and has_people:
                has_closed_eyes, eye_info = self.face_detector.detect_closed_eyes(image_path)
                result.details['eye_detection'] = eye_info
                if has_closed_eyes:
                    result.should_filter = True
                    result.reasons.append("Closed eyes detected")
        
        return result
    
    def find_duplicates(self, image_paths: List[str]) -> List[List[str]]:
        """
        Find duplicate images in a list.
        
        Args:
            image_paths: List of image file paths.
            
        Returns:
            List of duplicate groups.
        """
        if not self.config.check_duplicates:
            return []
        
        return self.duplicate_detector.find_duplicates(image_paths)
    
    def get_image_files(self, directory: str, recursive: bool = True) -> List[str]:
        """
        Get all supported image files from a directory.
        
        Args:
            directory: Path to directory to scan.
            recursive: Whether to scan subdirectories.
            
        Returns:
            List of image file paths.
        """
        image_files = []
        path = Path(directory)
        
        if recursive:
            pattern = "**/*"
        else:
            pattern = "*"
        
        for file_path in path.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in self.config.supported_extensions:
                image_files.append(str(file_path))
        
        return sorted(image_files)
    
    def filter_directory(self, directory: str, recursive: bool = True) -> Dict[str, FilterResult]:
        """
        Filter all images in a directory.
        
        Args:
            directory: Path to directory containing images.
            recursive: Whether to scan subdirectories.
            
        Returns:
            Dictionary mapping image paths to FilterResult objects.
        """
        image_files = self.get_image_files(directory, recursive)
        results = {}
        
        for image_path in image_files:
            result = self.filter_image(image_path)
            results[image_path] = result
        
        return results
    
    def save_results(self, results: Dict[str, FilterResult], output_file: str):
        """
        Save filtering results to a JSON file.
        
        Args:
            results: Dictionary of FilterResult objects.
            output_file: Path to output JSON file.
        """
        output_data = {
            'config': {
                'check_blur': self.config.check_blur,
                'blur_threshold': self.config.blur_threshold,
                'check_exposure': self.config.check_exposure,
                'check_resolution': self.config.check_resolution,
                'check_noise': self.config.check_noise,
                'check_duplicates': self.config.check_duplicates,
                'check_closed_eyes': self.config.check_closed_eyes,
                'filter_no_people': self.config.filter_no_people,
            },
            'results': []
        }
        
        for path, result in results.items():
            output_data['results'].append({
                'path': result.path,
                'should_filter': result.should_filter,
                'reasons': result.reasons,
                'details': result.details
            })
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
