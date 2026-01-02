"""
Command-line interface for phaicull photo culling tool.
"""

import argparse
import sys
import os
import shutil
from pathlib import Path
from typing import Optional
from tqdm import tqdm

from .filter import PhotoFilter, FilterConfig
from .__init__ import __version__


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        prog='phaicull',
        description='AI photo culling tool - Filter out blurred, dark, duplicate, and low-quality photos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze photos in a directory
  phaicull /path/to/photos
  
  # Move filtered photos to a separate folder
  phaicull /path/to/photos --action move --output /path/to/filtered
  
  # Only check for blur and duplicates
  phaicull /path/to/photos --no-exposure --no-resolution --no-noise
  
  # Filter photos without people
  phaicull /path/to/photos --filter-no-people
  
  # Adjust blur sensitivity (lower = more strict)
  phaicull /path/to/photos --blur-threshold 150
        """
    )
    
    parser.add_argument(
        'input_dir',
        help='Input directory containing photos to analyze'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    
    # Output options
    output_group = parser.add_argument_group('output options')
    output_group.add_argument(
        '--action',
        choices=['report', 'copy', 'move'],
        default='report',
        help='Action to take with filtered photos (default: report)'
    )
    output_group.add_argument(
        '--output',
        help='Output directory for filtered photos (required for copy/move actions)'
    )
    output_group.add_argument(
        '--report',
        default='filter_report.json',
        help='Path to save JSON report (default: filter_report.json)'
    )
    output_group.add_argument(
        '--keep-filtered',
        action='store_true',
        help='Keep filtered photos (action=move will move good photos instead)'
    )
    
    # Scanning options
    scan_group = parser.add_argument_group('scanning options')
    scan_group.add_argument(
        '--no-recursive',
        action='store_true',
        help='Do not scan subdirectories'
    )
    
    # Filter toggles
    filter_group = parser.add_argument_group('filter toggles')
    filter_group.add_argument(
        '--no-blur',
        action='store_true',
        help='Disable blur detection'
    )
    filter_group.add_argument(
        '--no-exposure',
        action='store_true',
        help='Disable exposure (dark/bright) detection'
    )
    filter_group.add_argument(
        '--no-resolution',
        action='store_true',
        help='Disable low resolution detection'
    )
    filter_group.add_argument(
        '--no-noise',
        action='store_true',
        help='Disable noise detection'
    )
    filter_group.add_argument(
        '--no-duplicates',
        action='store_true',
        help='Disable duplicate detection'
    )
    filter_group.add_argument(
        '--no-closed-eyes',
        action='store_true',
        help='Disable closed eyes detection'
    )
    filter_group.add_argument(
        '--filter-no-people',
        action='store_true',
        help='Filter out photos without people'
    )
    
    # Filter parameters
    param_group = parser.add_argument_group('filter parameters')
    param_group.add_argument(
        '--blur-threshold',
        type=float,
        default=100.0,
        help='Blur detection threshold (lower = more strict, default: 100.0)'
    )
    param_group.add_argument(
        '--dark-threshold',
        type=float,
        default=0.5,
        help='Dark photo threshold 0-1 (default: 0.5)'
    )
    param_group.add_argument(
        '--bright-threshold',
        type=float,
        default=0.5,
        help='Overexposed photo threshold 0-1 (default: 0.5)'
    )
    param_group.add_argument(
        '--min-width',
        type=int,
        default=800,
        help='Minimum acceptable width in pixels (default: 800)'
    )
    param_group.add_argument(
        '--min-height',
        type=int,
        default=600,
        help='Minimum acceptable height in pixels (default: 600)'
    )
    param_group.add_argument(
        '--noise-threshold',
        type=float,
        default=1000.0,
        help='Noise detection threshold (higher = more strict, default: 1000.0)'
    )
    param_group.add_argument(
        '--duplicate-similarity',
        type=int,
        default=5,
        help='Duplicate detection similarity (0-64, lower = more strict, default: 5)'
    )
    
    return parser


def process_photos(args):
    """Process photos based on command-line arguments."""
    
    # Validate input directory
    if not os.path.exists(args.input_dir):
        print(f"Error: Input directory '{args.input_dir}' does not exist", file=sys.stderr)
        return 1
    if not os.path.isdir(args.input_dir):
        print(f"Error: '{args.input_dir}' is not a directory", file=sys.stderr)
        return 1
    
    # Validate output directory for copy/move actions
    if args.action in ('copy', 'move'):
        if not args.output:
            print("Error: --output is required for copy/move actions", file=sys.stderr)
            return 1
        
        # Create output directory if it doesn't exist
        os.makedirs(args.output, exist_ok=True)
    
    # Create filter configuration
    config = FilterConfig(
        check_blur=not args.no_blur,
        blur_threshold=args.blur_threshold,
        check_exposure=not args.no_exposure,
        dark_threshold=args.dark_threshold,
        bright_threshold=args.bright_threshold,
        check_resolution=not args.no_resolution,
        min_width=args.min_width,
        min_height=args.min_height,
        check_noise=not args.no_noise,
        noise_threshold=args.noise_threshold,
        check_duplicates=not args.no_duplicates,
        duplicate_similarity=args.duplicate_similarity,
        check_closed_eyes=not args.no_closed_eyes,
        filter_no_people=args.filter_no_people
    )
    
    # Initialize photo filter
    photo_filter = PhotoFilter(config)
    
    # Get all image files
    print(f"Scanning directory: {args.input_dir}")
    image_files = photo_filter.get_image_files(args.input_dir, recursive=not args.no_recursive)
    print(f"Found {len(image_files)} image(s)")
    
    if not image_files:
        print("No images found to process")
        return 0
    
    # Process each image
    print("\nAnalyzing images...")
    results = {}
    for image_path in tqdm(image_files, desc="Processing", unit="image"):
        result = photo_filter.filter_image(image_path)
        results[image_path] = result
    
    # Find duplicates
    if config.check_duplicates:
        print("\nDetecting duplicates...")
        duplicate_groups = photo_filter.find_duplicates(image_files)
        
        # Mark duplicates (keep first, filter rest)
        for group in duplicate_groups:
            for dup_path in group[1:]:  # Skip first image in group
                if dup_path in results:
                    results[dup_path].should_filter = True
                    results[dup_path].reasons.append(f"Duplicate of {os.path.basename(group[0])}")
    
    # Generate statistics
    total_images = len(results)
    filtered_images = sum(1 for r in results.values() if r.should_filter)
    kept_images = total_images - filtered_images
    
    print(f"\n{'='*60}")
    print(f"Results Summary:")
    print(f"{'='*60}")
    print(f"Total images: {total_images}")
    print(f"Images to filter: {filtered_images}")
    print(f"Images to keep: {kept_images}")
    
    # Show filter reasons breakdown
    if filtered_images > 0:
        reason_counts = {}
        for result in results.values():
            if result.should_filter:
                for reason in result.reasons:
                    # Extract base reason (before any parentheses)
                    base_reason = reason.split('(')[0].strip()
                    reason_counts[base_reason] = reason_counts.get(base_reason, 0) + 1
        
        print(f"\nFilter reasons:")
        for reason, count in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {reason}: {count}")
    
    # Save report
    print(f"\nSaving report to: {args.report}")
    photo_filter.save_results(results, args.report)
    
    # Perform action on photos
    if args.action in ('copy', 'move'):
        print(f"\n{args.action.capitalize()}ing photos to: {args.output}")
        
        # Determine which photos to move/copy
        if args.keep_filtered:
            # Move/copy filtered photos
            photos_to_process = [path for path, r in results.items() if r.should_filter]
            action_desc = f"{args.action} filtered photos"
        else:
            # Move/copy kept photos
            photos_to_process = [path for path, r in results.items() if not r.should_filter]
            action_desc = f"{args.action} kept photos"
        
        for photo_path in tqdm(photos_to_process, desc=action_desc, unit="image"):
            # Preserve directory structure
            rel_path = os.path.relpath(photo_path, args.input_dir)
            dest_path = os.path.join(args.output, rel_path)
            
            # Create destination directory
            dest_dir = os.path.dirname(dest_path)
            if dest_dir:  # Only create if there's a directory component
                os.makedirs(dest_dir, exist_ok=True)
            
            # Copy or move
            if args.action == 'copy':
                shutil.copy2(photo_path, dest_path)
            else:  # move
                shutil.move(photo_path, dest_path)
        
        print(f"{args.action.capitalize()}d {len(photos_to_process)} photos")
    
    print(f"\n{'='*60}")
    print("Done!")
    
    return 0


def main():
    """Main entry point for CLI."""
    parser = create_parser()
    args = parser.parse_args()
    
    try:
        return process_photos(args)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
