# Quay Documentation

Quay is a Python library for Chrome DevTools automation with accessibility semantics.

## Quick Start

```python
from quay import Browser

browser = Browser()
browser.goto("https://example.com")
tree = browser.accessibility_tree()
print(tree.to_tree_str())
```

## Installation

```bash
pip install quay
```

## License

Apache-2.0
