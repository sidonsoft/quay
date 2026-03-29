# Agent Tasks — Quay

Step-by-step patterns for common maintenance tasks.

## Common Commands

```bash
cd ~/Code/quay

# Install in dev mode
pip install -e ".[dev]"     # with dev deps
pip install -e .             # core only

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=quay --cov-report=html --cov-report=term-missing

# Lint
ruff check .

# Format
ruff format .

# Type check
mypy quay/ --strict

# All validation
ruff check . && ruff format --check . && mypy quay/ --strict && pytest tests/ -v
```

## Common Tasks

### Adding a test

```python
def test_my_feature():
    """Description of what this tests."""
    # Test implementation
    assert result == expected
```

### Adding a module

1. Create `quay/mymodule.py`
2. Export in `quay/__init__.py`
3. Add tests in `tests/test_mymodule.py`
4. Run: `pytest tests/test_mymodule.py -v`

### Adding CLI command

1. Add argparse block in `quay/cli.py`
2. Add corresponding method in `quay/browser.py` if needed
3. Add test in `tests/test_cli.py`
4. Run full validation

## Architecture

```
quay/
├── quay/              # Core package
│   ├── browser.py     # CDP browser automation
│   ├── cli.py         # Command-line interface
│   ├── connection.py  # CDP WebSocket connection
│   ├── models.py      # Data models (Pydantic)
│   ├── errors.py      # Error types
│   └── evals.py       # Evaluation suite
├── tests/             # Test suite
└── scripts/           # Utility scripts
```

## CDP Patterns

```python
from quay import Browser

browser = Browser()
browser.new_tab("https://example.com")

# Get accessibility tree
tree = browser.accessibility_tree()
print(tree.to_tree_str())

# Interact
browser.click_by_text("Submit")
browser.fill_by_label("Email", "test@example.com")
browser.navigate("https://other.com")

# Screenshot
browser.save_screenshot("output.png")
```

## Version Bumping

```bash
# Update _version.py manually
# Add to CHANGELOG.md
# Tag:
git tag -a v0.x.x -m "Quay v0.x.x — description"
git push --tags
```
