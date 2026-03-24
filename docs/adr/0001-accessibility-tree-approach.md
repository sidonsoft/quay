# ADR-0001: Accessibility Tree for Element Targeting

## Status
Accepted

## Context

Browser automation tools typically use CSS selectors or XPath:

```python
# Playwright approach
page.click('button[data-testid="submit"]')

# Selenium approach
driver.find_element(By.CSS_SELECTOR, '.submit-btn')
```

**Problems with CSS selectors:**
1. Brittle — Frontend changes break selectors
2. Framework-specific — React/Vue/Angular generate different class names
3. Dynamic IDs — Changes between sessions
4. No semantic meaning

## Decision

We use the **accessibility tree** for element targeting:

```python
tree = browser.accessibility_tree()
print(tree.to_tree_str())
# - RootWebArea "GitHub" [ref=1]
#   - link "Sign in" [ref=42]
#   - textbox "Email" [ref=43]
#   - button "Submit" [ref=44]

browser.click("42")
browser.click_by_text("Sign in")
browser.type_by_name("Email", "user@example.com")
```

## Consequences

### Positive
- Stable across frontend changes
- Framework-agnostic
- Human-readable tree output
- Matches user perspective

### Negative
- Requires Chrome
- Extra CDP call to fetch tree
- Ref IDs change after navigation

## References
- [Chrome DevTools Protocol - Accessibility domain](https://chromedevtools.github.io/devtools-protocol/tot/Accessibility/)
- [agent-browser](https://github.com/nickyouttail/agent-browser)
