# Stealth Mode

Quay ships with three levels of stealth mode to reduce bot detection signals. All modes are enabled by default when you create a `Browser()` instance.

## Quick Start

```python
from quay import Browser

browser = Browser()
# Stealth (basic) + block_trackers are enabled by default
browser.goto("https://example.com")
browser.close()
```

## Stealth Levels

| Level | What it does | Performance cost |
|-------|--------------|-------------------|
| `basic` | Hides `navigator.webdriver`, removes CDP globals, stubs `window.chrome` | ~0ms |
| `balanced` | + Canvas/WebGL fingerprint spoofing, audio fingerprint protection | ~10-20ms |
| `aggressive` | + Screen dimension spoofing, MediaDevices spoofing, timing noise | ~30-50ms+ |

## Changing Stealth Mode

### At initialization

```python
browser = Browser(stealth_mode="balanced")
browser = Browser(stealth_mode="aggressive")
```

### At runtime

```python
browser = Browser()  # defaults to stealth=basic

# Switch to aggressive on next navigation
browser.set_stealth_mode("aggressive")
browser.goto("https://google.com")  # aggressive stealth applied here
```

Note: `set_stealth_mode()` takes effect on the **next page load**, not the current page. To re-apply to the current page, open a new tab or navigate to `about:blank` first.

### Disabling stealth

```python
browser = Browser(stealth=False)  # stealth completely disabled
```

## Blocklist

`block_trackers=True` (default) blocks these domains via CDP Network interception:

- Analytics & fingerprinting: `google-analytics.com`, `googletagmanager.com`, `facebook.net`, `hotjar.com`, `mixpanel.com`
- Bot detection: `distilnetworks.com`, `shapesecurity.com`, `riskified.com`, `arkose.com`
- CAPTCHA: `google.com/recaptcha`, `hcaptcha.com`, `friendlycaptcha.com`

## Verifying Stealth is Active

```python
browser = Browser()
browser.goto("https://example.com")

status = browser.is_stealth()
print(status)
# {'navigator.webdriver': None, 'webdriver': False, 'chrome.runtime': False, ...}
```

`navigator.webdriver` should be `None` (undefined) — if it's `True`, the page can detect automation.

## Stealth with a Real Chrome Profile

For harder-to-detect automation, use a real Chrome profile:

```python
browser = Browser(profile_path="/Users/you/Library/Application Support/Google/Chrome/Profile 1")
browser.goto("https://google.com")
```

This gives you Chrome's real cookies, fingerprints, and session state — far harder to detect than a fresh temp profile.

## Limitations

Stealth mode removes obvious automation signals but cannot make a bot undetectable:

- **CAPTCHA**: Google and DuckDuckGo also analyze behavior (mouse movement, typing speed, IP reputation, account history). Stealth removes the header signals but behavioral signals still exist.
- **Advanced fingerprinting**: Some sites use techniques beyond canvas/WebGL (e.g., timing-based CPU fingerprinting, font enumeration). Stealth covers the common vectors but not everything.
- **IP-based detection**: If your IP is flagged as a VPN or datacenter, no amount of stealth will help. Use residential proxies for hard targets.

For hard targets (Google, Cloudflare, Arkose), the most reliable approach is a real Chrome profile + residential proxy + human-like delays.
