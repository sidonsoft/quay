# Multi-Tab Workflows

Quay supports coordinated multi-tab operations for complex automation scenarios.

## Isolated Workflows with `temp_tab()`

The `temp_tab()` context manager is the recommended way to handle isolated, throwaway workflows. It ensures that tabs are cleaned up automatically after use.

```python
from quay import Browser

with Browser() as browser:
    with browser.temp_tab("https://www.google.com") as tab:
        browser.type_by_name("Search", "python browser automation")
        browser.press_key("Enter")
        browser.wait_for_load_state()

        # Extract data from the isolated tab
        results = browser.get_html()
        print(f"Collected {len(results)} characters of HTML")

    # Tab is automatically closed here!
```

## Context Switching with `switch_to_tab()`

When working with multiple long-lived tabs, `switch_to_tab()` allows you to jump between them while tracking the previous state.

```python
# Create two working tabs
tab1 = browser.goto("https://github.com")
tab2 = browser.goto("https://news.ycombinator.com")

# Switch to GitHub
previous = browser.switch_to_tab(tab1)

# Do some work...
browser.click_by_text("Sign in")

# Switch back to HN
browser.switch_to_tab(previous)
```

## Common Design Patterns

### Parallel Data Collection (Sequential)

```python
urls = ["https://site-a.com", "https://site-b.com"]
data = []

for url in urls:
    with browser.temp_tab(url) as tab:
        browser.wait_for_load_state()
        data.append({
            "url": url,
            "title": tab.title,
            "tree": browser.accessibility_tree().to_dict()
        })
```

### Monitoring Background Changes

```python
with browser.temp_tab("https://dashboard.example.com", close_on_exit=False) as dashboard:
    # Do work in main tab...
    browser.goto("https://task-manager.com")

    # Briefly check dashboard
    browser.switch_to_tab(dashboard)
    if "Alert" in browser.get_html():
        print("Dashboard needs attention!")

    browser.activate_tab(main_tab_id)
```

## Best Practices

1. **Always use `temp_tab()`** for secondary tasks to ensure your browser does not end up with dozens of stale tabs.
2. **Explicitly pass `tab`** to specific methods if you are doing complex multi-tab logic.
3. **Use `close_on_exit=False`** sparingly when you need to inspect the final state of a tab after a complex interaction.
