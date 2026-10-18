# Installation

## Requirements

- Python 3.10 or higher
- Chrome or Chromium browser
- Remote debugging enabled in Chrome

## Install Package

```bash
pip install quay
```

## Enable Chrome Remote Debugging

Quay connects to Chrome via the Chrome DevTools Protocol. You must start Chrome with remote debugging enabled.

⚠️ **Chrome 136+**: `--remote-debugging-port` is ignored when used against Chrome's **default profile**. Always pass a separate `--user-data-dir` as shown below. Sign in once in that debug profile — your session then persists there.

⚠️ **Chrome 144+**: Google added a consent flow when a debugger attaches to an already-running Chrome. Two options:

1. **Launch Chrome with the flags below (recommended)** — the debug port is open from startup and no prompt appears.
2. **Attach to your normal running Chrome** — first enable remote debugging at `chrome://inspect/#remote-debugging`, then approve the permission prompt Chrome shows for *every* connection (approval cannot be persisted yet, see [chrome-devtools-mcp#825](https://github.com/ChromeDevTools/chrome-devtools-mcp/issues/825)).

### macOS

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="$HOME/.quay/chrome-debug-profile" &
```

Or create a shortcut:

```bash
# Add to ~/.zshrc or ~/.bashrc
alias chrome-debug='/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="$HOME/.quay/chrome-debug-profile"'
```

### Linux

```bash
google-chrome --remote-debugging-port=9222 --user-data-dir="$HOME/.quay/chrome-debug-profile" &

# Or chromium
chromium --remote-debugging-port=9222 --user-data-dir="$HOME/.quay/chrome-debug-profile" &
```

### Windows

```powershell
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\.quay\chrome-debug-profile"
```

## Verify Connection

```python
from quay import Browser

browser = Browser()
tabs = browser.list_tabs()
print(f"Connected! Found {len(tabs)} tabs")
browser.close()
```

## Development Install

For contributing or local development:

```bash
git clone https://github.com/sidonsoft/quay
cd quay
pip install -e ".[dev]"
```

## Optional Dependencies

The core package has minimal dependencies:

- `websockets>=12.0` — WebSocket client for CDP
- `pyyaml>=6.0` — Configuration parsing

Development dependencies:

```bash
pip install -e ".[dev]"  # Includes pytest, ruff, ty
```

## Troubleshooting

### "No Chrome found"

Make sure Chrome is running with `--remote-debugging-port=9222`.

### "Connection refused"

Check that nothing else is using port 9222:

```bash
lsof -i :9222
```

### "Multiple Chrome instances"

If you see "Chrome is already running", close all Chrome windows and restart with the flag:

```bash
pkill -f Chrome
chrome --remote-debugging-port=9222 &
```
