# Visual Regression Testing

Quay supports visual regression testing through pixel-by-pixel screenshot comparison.

> **⚠️ Basic Implementation**
>
> Screenshot comparison uses byte-by-byte comparison. No perceptual diff or threshold-based comparison yet. For advanced visual testing, consider integrating with tools like Percy or Applitools.

## Installation

Visual comparison requires the `compare` extra dependencies:

```bash
pip install quay[compare]
```

Or install `Pillow` and `numpy` manually.

## Basic Comparison

```python
from quay import Browser

browser = Browser()
result = browser.compare_screenshots("baseline.png", "current.png")

if result.match:
    print("Screenshots match exactly!")
else:
    print(f"Differences detected: {result.diff_percentage:.2f}%")
    print(f"Total differing pixels: {result.diff_pixels}")
```

## Tolerance Thresholds

UI rendering can vary slightly. Set a `threshold` (0.0 to 100.0) to allow a certain percentage of differing pixels.

```python
# Allow up to 0.5% difference
result = browser.assert_visual_match("baseline.png", threshold=0.5)
```

## Visual Diffs

When a comparison fails, use `output_diff` to generate a diff image where differences are highlighted in red.

```python
result = browser.compare_screenshots(
    "baseline.png",
    "current.png",
    output_diff="diff.png"
)
```

## Partial Comparison (Regions)

Compare a specific part of the page using the `region` parameter.

```python
# Compare a 500x400 area starting at (100, 100)
result = browser.compare_screenshots(
    "baseline.png",
    "current.png",
    region=(100, 100, 500, 400)
)
```

## CI/CD Workflow

```python
def test_dashboard_visual():
    browser = Browser()
    browser.goto("https://myapp.com/dashboard")

    # This will raise AssertionError if they don't match
    browser.assert_visual_match("tests/baselines/dashboard.png", threshold=0.1)
```

### Updating Baselines

```python
# Update baseline with current view
browser.assert_visual_match("tests/baselines/dashboard.png", update_baseline=True)
```

## Comparison Metrics

| Property | Description |
|----------|-------------|
| `match` | True if diff_percentage <= threshold |
| `diff_pixels` | Total count of changed pixels |
| `diff_percentage` | Percentage of changed pixels |
| `baseline_size` | Tuple of (width, height) for baseline |
| `current_size` | Tuple of (width, height) for current |
| `diff_path` | Path to the generated diff image |
| `message` | Human-readable summary |
