# Feature: Anti-Detection Stealth Mode

## Problem
Sites like BBC, Google, and banking portals detect and block standard Chrome CDP sessions because automation reveals itself through `navigator.webdriver`, `webdriver` property, automation-controlled flags, and more. Users need a way to run Chrome that looks like a real browser session.

## Goal
`Browser(stealth=True)` launches a Chrome profile that resists bot detection out of the box.

## Implementation

### 1. Chrome Launch Args
When `stealth=True`, pass these flags to the Chrome process:

```
--disable-blink-features=AutomationControlled
--disable-infobars
--disable-dev-shm-usage
--no-sandbox
--disable-setuid-sandbox
--disable-gpu
--window-size=1920,1080
```

### 2. CDP Page.addScriptToEvaluateOnNewDocument
After each new tab, inject a script to remove automation signals before any JS runs:

```javascript
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Chart;
delete window.__webdriver_evaluate;
delete window.__selenium_evaluate;
delete window.__webdriver_script_function;
delete window.__webdriver_script_func;
delete window.__webdriver_script_fn;
```

### 3. Block Bot Detection Scripts
Use CDP `Network.requestIntercepted` or set of interceptor rules to block known bot detection endpoints (optional, can be a separate `block_trackers=True` flag).

## API Design

```python
from quay import Browser

# Stealth mode — resists detection
b = Browser(stealth=True)

# Stealth + block known trackers
b = Browser(stealth=True, block_trackers=True)

# No stealth (default)
b = Browser()
```

## Files Affected
- `quay/browser.py` — `Browser.__init__()`: add `stealth`, `block_trackers` params
- `quay/browser.py` — `new_tab()`: inject CDP stealth script on new document
- `quay/chrome.py` (new or existing) — Chrome process launch with stealth args

## Notes
- Stealth mode should be opt-in (default `False`) to preserve current behavior for users who need visibility
- The CDP script injection must happen on `Page.frameNavigated` or `Page.load`, before any site JS executes
- Consider using an existing stealth profile dir rather than ephemeral to appear more "real"
