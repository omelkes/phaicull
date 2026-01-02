# Examples

This document provides practical examples of using phaicull for different scenarios.

## Basic Examples

### Example 1: Quick Analysis

Analyze all photos in a directory and generate a report:

```bash
phaicull /path/to/photos
```

This will:
- Scan all images recursively
- Check for all quality issues (blur, exposure, resolution, noise, duplicates, closed eyes)
- Generate `filter_report.json` with detailed results
- Print summary statistics

### Example 2: Organize Good Photos

Move all good (non-filtered) photos to a new directory:

```bash
phaicull /path/to/photos --action move --output /path/to/good_photos
```

This will:
- Analyze all photos
- Move high-quality photos to `/path/to/good_photos`
- Leave filtered photos in the original directory
- Preserve directory structure

### Example 3: Review Filtered Photos

Copy photos flagged for filtering to review them manually:

```bash
phaicull /path/to/photos --action copy --output /path/to/review --keep-filtered
```

This will:
- Copy all filtered photos to `/path/to/review`
- Keep original photos untouched
- Allow you to manually review before deleting

## Filtering Specific Issues

### Example 4: Only Check for Blur

```bash
phaicull /path/to/photos \
  --no-exposure \
  --no-resolution \
  --no-noise \
  --no-duplicates \
  --no-closed-eyes
```

### Example 5: Find Duplicates Only

```bash
phaicull /path/to/photos \
  --no-blur \
  --no-exposure \
  --no-resolution \
  --no-noise \
  --no-closed-eyes
```

### Example 6: Quality Check (Blur + Exposure + Resolution)

```bash
phaicull /path/to/photos \
  --no-noise \
  --no-duplicates \
  --no-closed-eyes
```

## Adjusting Sensitivity

### Example 7: Strict Blur Detection

Filter more aggressively (higher threshold = keep more photos):

```bash
phaicull /path/to/photos --blur-threshold 150
```

Filter less aggressively (lower threshold = filter more photos):

```bash
phaicull /path/to/photos --blur-threshold 50
```

### Example 8: Custom Resolution Requirements

For HD photos only (1920x1080):

```bash
phaicull /path/to/photos --min-width 1920 --min-height 1080
```

For lower resolution threshold:

```bash
phaicull /path/to/photos --min-width 640 --min-height 480
```

### Example 9: Aggressive Duplicate Detection

Use a stricter threshold (lower = more strict):

```bash
phaicull /path/to/photos --duplicate-similarity 3
```

Use a more lenient threshold:

```bash
phaicull /path/to/photos --duplicate-similarity 10
```

## Real-World Scenarios

### Example 10: Family Photos - Keep Only Photos with People

```bash
phaicull /path/to/family_photos \
  --filter-no-people \
  --action move \
  --output /path/to/family_photos_filtered
```

### Example 11: Event Photos - Remove Blur and Closed Eyes

```bash
phaicull /path/to/event_photos \
  --no-resolution \
  --no-noise \
  --no-duplicates \
  --action move \
  --output /path/to/event_photos_cleaned
```

### Example 12: Vacation Photos - Keep Best Quality

```bash
phaicull /path/to/vacation \
  --blur-threshold 120 \
  --min-width 1280 \
  --min-height 720 \
  --action move \
  --output /path/to/vacation_best
```

### Example 13: Quick Cleanup Before Sharing

Remove obviously bad photos quickly:

```bash
phaicull /path/to/photos \
  --blur-threshold 80 \
  --no-closed-eyes \
  --no-noise \
  --action move \
  --output /path/to/shareable
```

### Example 14: Archive Management - Find Space Wasters

Find duplicates and low-quality images:

```bash
phaicull /path/to/archive \
  --no-closed-eyes \
  --action copy \
  --output /path/to/to_delete \
  --keep-filtered
```

## Advanced Usage

### Example 15: Process Single Directory (No Subdirectories)

```bash
phaicull /path/to/photos --no-recursive
```

### Example 16: Custom Report Location

```bash
phaicull /path/to/photos --report /path/to/reports/analysis_$(date +%Y%m%d).json
```

### Example 17: Process and Review in Steps

Step 1: Generate report
```bash
phaicull /path/to/photos --report analysis.json
```

Step 2: Review the JSON report
```bash
cat analysis.json | python -m json.tool | less
```

Step 3: After confirming, move good photos
```bash
phaicull /path/to/photos --action move --output /path/to/good_photos
```

### Example 18: Batch Processing Multiple Directories

```bash
#!/bin/bash
# Process multiple photo directories

for dir in 2020 2021 2022 2023; do
  echo "Processing $dir..."
  phaicull /photos/$dir \
    --action move \
    --output /photos_filtered/$dir \
    --report /reports/${dir}_report.json
done
```

### Example 19: Conservative Filtering (Only Obvious Issues)

```bash
phaicull /path/to/photos \
  --blur-threshold 50 \
  --dark-threshold 0.7 \
  --bright-threshold 0.7 \
  --duplicate-similarity 2 \
  --action move \
  --output /path/to/kept_photos
```

### Example 20: Aggressive Cleanup (Maximum Filtering)

```bash
phaicull /path/to/photos \
  --blur-threshold 150 \
  --dark-threshold 0.3 \
  --bright-threshold 0.3 \
  --min-width 1920 \
  --min-height 1080 \
  --duplicate-similarity 8 \
  --action move \
  --output /path/to/premium_quality
```

## Tips

1. **Always test first**: Run with `--action report` before using `move` to see what will be filtered
2. **Backup important photos**: Make backups before using `--action move`
3. **Review filtered photos**: Use `--keep-filtered` with `copy` to review what's being filtered
4. **Adjust thresholds**: Different photo collections may need different sensitivity settings
5. **Process incrementally**: For large collections, test on a subset first
6. **Check the JSON report**: It contains detailed information about why each photo was filtered

## Getting Help

For more options and details:

```bash
phaicull --help
```

To see the version:

```bash
phaicull --version
```
