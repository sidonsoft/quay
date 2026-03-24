# Benchmark Guide

quay is optimized for low-latency, real-world interactions. The benchmark suite compares quay against common automation tools.

## Setup

```bash
# Install quay in editable mode
pip install -e .

# Install competitors
pip install playwright && playwright install chromium
pip install selenium
```

Your Chrome instance **must** be running with `--remote-debugging-port=9222`.

## Running Benchmarks

```bash
python -m benchmarks.run_benchmarks
```

Options:
- `--scenarios`: Filter specific scenarios
- `--runs`: Number of iterations per tool (default: 10)
- `--results-dir`: Custom directory for JSON results
- `--output`: Format (table, json, markdown)

## Available Scenarios

| Scenario | Description |
| :--- | :--- |
| `navigation` | Cold navigation to simple and JS-heavy pages |
| `accessibility_tree` | Time to fetch and parse the semantic AX tree |
| `click_performance` | Latency of text-based and ref-based clicks |
| `form_fill` | Speed of typing and filling multiple complex forms |
| `screenshot` | Time to capture both viewport and full-page screenshots |

## Comparison Tool

```bash
cd quay
python benchmarks/compare.py results/*.json
```

## Adding New Scenarios

1. Create a new file in `benchmarks/scenarios/`.
2. Inherit from `BaseScenario`.
3. Implement the `run()` and `teardown()` methods.
4. Add the scenario to the `SCENARIOS` registry.

```python
from benchmarks.scenarios.base import BaseScenario

class CustomScenario(BaseScenario):
    def run(self, browser, page_url):
        with self.timer("total_interaction"):
            browser.click_by_text("Special Interaction")
```

## Interpreting Results

- `mean_ms`: Average latency. Focus on this for overall responsiveness.
- `p95_ms`: 95th percentile latency. Critical for identifying jitter.
- `success_rate`: Reliability measure. Ensure tools are completing tasks.
