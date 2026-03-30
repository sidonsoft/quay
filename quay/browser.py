"""
Browser Hybrid - Chrome DevTools Protocol automation.

Provides hybrid browser automation combining Chrome DevTools
WebSocket control with accessibility-tree semantic understanding.

Limitations:
- Only handles tabs within a single Chrome window
- Multiple Chrome windows are not supported
- Use Chrome's --new-window flag or ensure all tabs are in one window

For multi-window scenarios, consider using multiple Browser instances.

Example:
    from quay import Browser

    browser = Browser()
    browser.new_tab("https://gmail.com")

    tree = browser.accessibility_tree()
    print(tree.to_tree_str())

    browser.click_by_text("Sign in")
"""

from __future__ import annotations

import asyncio
import atexit
import base64
import contextvars
import datetime
import json
import logging
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

from ._version import __version__
from .connection import Connection
from .connection import ConnectionPool
from .connection import ConnectionState
from .errors import BrowserError
from .errors import CDPError
from .errors import ConnectionError
from .errors import TabError
from .errors import TimeoutError
from .errors import parse_cdp_error
from .models import Action
from .models import AXNode
from .models import BrowserInfo
from .models import ComparisonResult
from .models import Recording
from .models import Tab

__all__ = [
    "Browser",
    "Tab",
    "AXNode",
    "BrowserInfo",
    "Action",
    "Recording",
    "ComparisonResult",
    "BrowserError",
    "ConnectionError",
    "TabError",
    "TimeoutError",
    "CDPError",
]

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 9222
DEFAULT_TIMEOUT = 10.0

# Device descriptors for mobile emulation
# Based on Chrome DevTools device descriptors
_DEVICES = {
    "iPhone 14 Pro": {
        "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "viewport": {"width": 393, "height": 852, "deviceScaleFactor": 3, "flexible": False},
        "touch": True,
        "mobile": True,
    },
    "iPhone 14": {
        "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "viewport": {"width": 390, "height": 844, "deviceScaleFactor": 3, "flexible": False},
        "touch": True,
        "mobile": True,
    },
    "iPhone SE": {
        "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
        "viewport": {"width": 320, "height": 568, "deviceScaleFactor": 2, "flexible": False},
        "touch": True,
        "mobile": True,
    },
    "iPad Pro 12.9": {
        "userAgent": "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "viewport": {"width": 1024, "height": 1366, "deviceScaleFactor": 2, "flexible": False},
        "touch": True,
        "mobile": True,
    },
    "iPad Air": {
        "userAgent": "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "viewport": {"width": 820, "height": 1180, "deviceScaleFactor": 2, "flexible": False},
        "touch": True,
        "mobile": True,
    },
    "Samsung Galaxy S21": {
        "userAgent": "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36",
        "viewport": {"width": 360, "height": 800, "deviceScaleFactor": 3, "flexible": False},
        "touch": True,
        "mobile": True,
    },
    "Samsung Galaxy S20": {
        "userAgent": "Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36",
        "viewport": {"width": 360, "height": 800, "deviceScaleFactor": 3, "flexible": False},
        "touch": True,
        "mobile": True,
    },
    "Google Pixel 7": {
        "userAgent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36",
        "viewport": {"width": 412, "height": 915, "deviceScaleFactor": 2.625, "flexible": False},
        "touch": True,
        "mobile": True,
    },
    "Google Pixel 6": {
        "userAgent": "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Mobile Safari/537.36",
        "viewport": {"width": 412, "height": 915, "deviceScaleFactor": 2.625, "flexible": False},
        "touch": True,
        "mobile": True,
    },
    "Motorola Moto G4": {
        "userAgent": "Mozilla/5.0 (Linux; Android 7.0; Moto G (4)) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Mobile Safari/537.36",
        "viewport": {"width": 720, "height": 1280, "deviceScaleFactor": 2, "flexible": False},
        "touch": True,
        "mobile": True,
    },
}

# Stealth script to hide automation signals from pages
# Basic mode - essential anti-detection
_STEALTH_SCRIPT_BASIC = """
(function() {
  // Override the webdriver property
  Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
  });

  // Remove automation-related properties
  Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5]
  });

  Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en']
  });

  // Remove CDP-related globals
  delete window.cdc_adoQpoasnfa76pfcZLmcfl_Chart;
  delete window.__PuppeteerOverlayObject__;
  delete window.__PuppeteerIsHeadless__;
  delete window.__isCdpEnabled__;

  // Remove window.webdriver (separate from navigator.webdriver)
  delete window.webdriver;

  // Override the chrome object — replace entirely to avoid read-only issues
  window.chrome = { runtime: undefined };
})();
"""

# Balanced mode - adds canvas/audio fingerprinting prevention
_STEALTH_SCRIPT_BALANCED = """
(function() {
  // Override the webdriver property
  Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
  });

  // Remove automation-related properties
  Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5]
  });

  Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en']
  });

  // Remove CDP-related globals
  delete window.cdc_adoQpoasnfa76pfcZLmcfl_Chart;
  delete window.__PuppeteerOverlayObject__;
  delete window.__PuppeteerIsHeadless__;
  delete window.__isCdpEnabled__;

  // Remove window.webdriver (separate from navigator.webdriver)
  delete window.webdriver;

  // Override the chrome object — replace entirely to avoid read-only issues
  window.chrome = { runtime: undefined };

  // Mock permissions
  const originalQuery = window.navigator.permissions.query;
  window.navigator.permissions.query = (parameters) => {
    return (parameters.name === 'notifications') ?
      Promise.resolve({ state: Notification.permission }) :
      originalQuery(parameters);
  };

  // Mock webgl vendor
  const getParameter = WebGLRenderingContext.prototype.getParameter;
  WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) {
      return 'Intel Inc.';
    }
    if (parameter === 37446) {
      return 'Intel Iris OpenGL Engine';
    }
    return getParameter(parameter);
  };

  // Canvas fingerprinting prevention
  const toDataURL = HTMLCanvasElement.prototype.toDataURL;
  HTMLCanvasElement.prototype.toDataURL = function() {
    if (arguments.length > 0 && typeof arguments[0] === 'string' && arguments[0].startsWith('image/')) {
      return toDataURL.apply(this, ['image/png']);
    }
    return toDataURL.apply(this, arguments);
  };

  // AudioContext fingerprinting prevention
  const AudioContextConstructor = window.AudioContext || window.webkitAudioContext;
  if (AudioContextConstructor) {
    window.AudioContext = function() {
      const audioContext = new AudioContextConstructor();
      const originalGetDestination = audioContext.destination;
      Object.defineProperty(audioContext, 'destination', {
        get: () => originalGetDestination
      });
      return audioContext;
    };
    window.AudioContext.prototype = AudioContextConstructor.prototype;
  }
})();
"""

# Aggressive mode - all anti-detection techniques
_STEALTH_SCRIPT_AGGRESSIVE = """
(function() {
  // Override the webdriver property
  Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
  });

  // Remove automation-related properties
  Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5]
  });

  Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en']
  });

  // Remove CDP-related globals
  delete window.cdc_adoQpoasnfa76pfcZLmcfl_Chart;
  delete window.__PuppeteerOverlayObject__;
  delete window.__PuppeteerIsHeadless__;
  delete window.__isCdpEnabled__;

  // Remove window.webdriver (separate from navigator.webdriver)
  delete window.webdriver;

  // Override the chrome object — replace entirely to avoid read-only issues
  window.chrome = { runtime: undefined };

  // Mock permissions
  const originalQuery = window.navigator.permissions.query;
  window.navigator.permissions.query = (parameters) => {
    return (parameters.name === 'notifications') ?
      Promise.resolve({ state: Notification.permission }) :
      originalQuery(parameters);
  };

  // Mock webgl vendor
  const getParameter = WebGLRenderingContext.prototype.getParameter;
  WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) {
      return 'Intel Inc.';
    }
    if (parameter === 37446) {
      return 'Intel Iris OpenGL Engine';
    }
    return getParameter(parameter);
  };

  // Canvas fingerprinting prevention
  const toDataURL = HTMLCanvasElement.prototype.toDataURL;
  HTMLCanvasElement.prototype.toDataURL = function() {
    if (arguments.length > 0 && typeof arguments[0] === 'string' && arguments[0].startsWith('image/')) {
      return toDataURL.apply(this, ['image/png']);
    }
    return toDataURL.apply(this, arguments);
  };

  // AudioContext fingerprinting prevention
  const AudioContextConstructor = window.AudioContext || window.webkitAudioContext;
  if (AudioContextConstructor) {
    window.AudioContext = function() {
      const audioContext = new AudioContextConstructor();
      const originalGetDestination = audioContext.destination;
      Object.defineProperty(audioContext, 'destination', {
        get: () => originalGetDestination
      });
      return audioContext;
    };
    window.AudioContext.prototype = AudioContextConstructor.prototype;
  }

  // Screen dimensions spoofing
  const screenGet = Object.getOwnPropertyDescriptor(Screen.prototype, 'width');
  Object.defineProperty(screenGet, 'get', {
    value: function() {
      return 1920;
    }
  });
  Object.defineProperty(screenGet, 'set', {
    value: undefined
  });

  // Performance API override
  const originalPerformanceTiming = PerformanceTiming.prototype;
  Object.defineProperty(PerformanceTiming.prototype, 'navigationStart', {
    get: function() {
      return Date.now() - Math.random() * 1000;
    }
  });

  // Notification API override
  const originalNotification = window.Notification;
  if (originalNotification) {
    window.Notification.requestPermission = function() {
      return Promise.resolve('granted');
    };
  }

  // MediaDevices API spoofing
  const originalGetDevices = navigator.mediaDevices.enumerateDevices;
  navigator.mediaDevices.enumerateDevices = function() {
    return originalGetDevices.call(navigator.mediaDevices).then(devices => {
      return devices.map(device => {
        // Spoof device IDs to prevent fingerprinting
        return {
          ...device,
          deviceId: 'spoofed_' + Math.random().toString(36).substr(2, 9),
          label: 'Default Device ' + device.kind
        };
      });
    });
  };
})();
"""

# Blocklist of known bot detection and tracking domains
# These are blocked via CDP Network interception when block_trackers=True
_BLOCKLIST = [
    # Analytics & Fingerprinting
    "google-analytics.com",
    "googletagmanager.com",
    "facebook.net",
    "hotjar.com",
    "mixpanel.com",
    "newrelic.com",
    "segment.io",
    # Bot Detection
    "distilnetworks.com",
    "shapesecurity.com",
    "riskified.com",
    "arkose.com",
    # CAPTCHA (optional — comment out if you need them)
    "google.com/recaptcha",
    "hcaptcha.com",
    "friendlycaptcha.com",
]


def escape_js_string(text: str) -> str:
    """
    Escape string for safe injection into JavaScript single/double quotes.

    Args:
        text: String to escape

    Returns:
        Escaped string
    """
    return (
        text.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace('"', '\\"')
        .replace("`", "\\`")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


AX_REF_PATTERN = re.compile(r"^(axnode@)?\d+$")


def _validate_ref(ref: str) -> None:
    """Validate accessibility ref format.

    Accepts both 'axnode@123' and plain '123' formats since Chrome's
    CDP returns plain numeric IDs but some APIs may use the prefixed format.
    """
    if not AX_REF_PATTERN.match(ref):
        raise ValueError(
            f"Invalid ref format: {ref!r}. Expected format: 'axnode@<number>' or '<number>'"
        )


def _get_chrome_path() -> str:
    """
    Get Chrome executable path based on OS.

    Returns:
        Path to Chrome executable

    Raises:
        FileNotFoundError: If Chrome is not found
    """
    import platform

    os_name = platform.system()

    if os_name == "Darwin":  # macOS
        paths = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    elif os_name == "Windows":
        paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
    elif os_name == "Linux":
        paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
        ]
    else:
        raise OSError(f"Unsupported OS: {os_name}")

    for path in paths:
        if os.path.exists(path):
            return path

    raise FileNotFoundError(
        f"Chrome not found. Expected at one of: {', '.join(paths)}"
    )


def _launch_chrome(
    headless: bool = False,
    stealth: bool = False,
    block_trackers: bool = False,
    port: int = 9222,
    user_data_dir: str | None = None,
) -> tuple[str, str]:
    """
    Launch Chrome with appropriate flags for automation.

    Args:
        headless: Run in headless mode
        stealth: Enable stealth mode (hides automation signals)
        block_trackers: Block known tracking/bot detection domains
        port: Remote debugging port
        user_data_dir: User data directory (None = temp profile)

    Returns:
        Tuple of (chrome_path, remote_debugging_url)

    Raises:
        FileNotFoundError: If Chrome is not found
        subprocess.SubprocessError: If Chrome fails to launch
    """
    import subprocess
    import tempfile

    chrome_path = _get_chrome_path()

    # Build flags
    flags = [
        chrome_path,
        f"--remote-debugging-port={port}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-default-apps",
        "--disable-sync",
        "--disable-translate",
        "--metrics-recording-only",
        "--disable-extensions",
        "--disable-dev-shm-usage",
    ]

    # Headless mode
    if headless:
        flags.append("--headless=new")
    else:
        flags.append("--start-maximized")

    # Stealth mode flags
    if stealth:
        flags.extend([
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
        ])

    # User data directory
    if user_data_dir:
        flags.extend(["--user-data-dir=" + user_data_dir])
    else:
        # Create temporary profile
        temp_dir = tempfile.mkdtemp(prefix="quay_chrome_profile_")
        flags.extend(["--user-data-dir=" + temp_dir])

    # Launch Chrome
    logger.info("Launching Chrome: %s", " ".join(flags[:2]) + "...")

    try:
        process = subprocess.Popen(
            flags,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
        )

        # Wait for Chrome to be ready
        import time

        for _ in range(30):  # 30 second timeout
            time.sleep(1)
            try:
                urllib.request.urlopen(f"http://localhost:{port}/json/version")
                logger.info("Chrome launched successfully on port %d", port)
                return chrome_path, f"http://localhost:{port}"
            except (urllib.error.URLError, ConnectionRefusedError):
                continue

        raise RuntimeError("Chrome failed to start within 30 seconds")

    except Exception as e:
        logger.error("Chrome launch error: %s", e)
        raise



# Key name to CDP key definition mapping
_KEY_MAP = {
    "Enter": {"key": "Enter", "code": "Enter", "keyCode": 13, "text": "\r"},
    "Tab": {"key": "Tab", "code": "Tab", "keyCode": 9},
    "Escape": {"key": "Escape", "code": "Escape", "keyCode": 27},
    "Backspace": {"key": "Backspace", "code": "Backspace", "keyCode": 8},
    "Delete": {"key": "Delete", "code": "Delete", "keyCode": 46},
    "ArrowUp": {"key": "ArrowUp", "code": "ArrowUp", "keyCode": 38},
    "ArrowDown": {"key": "ArrowDown", "code": "ArrowDown", "keyCode": 40},
    "ArrowLeft": {"key": "ArrowLeft", "code": "ArrowLeft", "keyCode": 37},
    "ArrowRight": {"key": "ArrowRight", "code": "ArrowRight", "keyCode": 39},
    "Home": {"key": "Home", "code": "Home", "keyCode": 36},
    "End": {"key": "End", "code": "End", "keyCode": 35},
    "PageUp": {"key": "PageUp", "code": "PageUp", "keyCode": 33},
    "PageDown": {"key": "PageDown", "code": "PageDown", "keyCode": 34},
    "Space": {"key": " ", "code": "Space", "keyCode": 32},
}


def _key_to_key_definition(key: str, modifiers: int = 0) -> dict:
    """
    Convert a key name to CDP dispatchKeyEvent key definition.

    Args:
        key: Key name (e.g., "a", "Enter", "Tab")
        modifiers: Bit flags for modifiers (Alt=1, Control=2, Meta=4, Shift=8)

    Returns:
        CDP key definition dict
    """
    # Single character - use as-is
    if len(key) == 1:
        return {
            "key": key,
            "code": f"Key{key.upper()}" if key.isalpha() else key,
            "text": key,
            "modifiers": modifiers,
        }

    # Named keys
    if key in _KEY_MAP:
        return {**_KEY_MAP[key], "modifiers": modifiers}

    # F1-F12
    if key.startswith("F") and key[1:].isdigit():
        num = int(key[1:])
        if 1 <= num <= 12:
            return {
                "key": key,
                "code": key,
                "keyCode": 112 + num - 1,
                "modifiers": modifiers,
            }

    # Unknown key - pass through
    return {"key": key, "code": key, "modifiers": modifiers}


logger = logging.getLogger(__name__)


# JavaScript helper functions (kept as module-level for readability)
# CDP JavaScript templates.
# NOTE: These are module-level constants. They MUST NEVER be mutated at runtime.
# Always use .replace() to create a new, safe string for specific invocations.
_CLICK_BY_TEXT_JS = """
(function() {
    var text = '{text}'.toLowerCase();

    function matchesText(el) {
        if (!el) return false;
        var inner = (el.innerText || el.textContent || "").toLowerCase();
        if (inner.includes(text)) return true;

        var aria = (el.getAttribute('aria-label') || "").toLowerCase();
        if (aria.includes(text)) return true;

        var value = (el.value || "").toString().toLowerCase();
        if (value.includes(text)) return true;

        var labelBy = el.getAttribute('aria-labelledby');
        if (labelBy) {
            var labelEl = document.getElementById(labelBy);
            if (labelEl) {
                var labelContent = labelEl.innerText || labelEl.textContent || "";
                if (labelContent.toLowerCase().includes(text)) return true;
            }
        }

        return false;
    }

    function performClick(el) {
        if (!el) return false;
        if ('{double}' === 'True') {
            el.dispatchEvent(new MouseEvent('dblclick', {bubbles: true}));
        } else if ('{button}' === 'right') {
            el.dispatchEvent(new MouseEvent('contextmenu', {bubbles: true}));
        } else {
            el.click();
        }
        return true;
    }

    // Try links first
    var links = document.querySelectorAll('a');
    for (var i = 0; i < links.length; i++) {
        if (matchesText(links[i])) {
            return performClick(links[i]);
        }
    }

    // Try buttons
    var buttons = document.querySelectorAll(
        'button, input[type=button], input[type=submit], input[type=reset]'
    );
    for (var j = 0; j < buttons.length; j++) {
        if (matchesText(buttons[j])) {
            return performClick(buttons[j]);
        }
    }

    // Try any element with exact text
    var all = document.querySelectorAll('*');
    for (var k = 0; k < all.length; k++) {
        var elText = (all[k].innerText || all[k].textContent || "").trim().toLowerCase();
        if (elText === text) {
            if (typeof all[k].click === 'function') {
                return performClick(all[k]);
            }
        }
    }
    return false;
})();
"""

_FIND_FORM_ELEMENT_JS = """
(function() {
    var identifier = '{identifier}';
    var lowerIdentifier = identifier.toLowerCase().trim();

    function elementMatches(el) {
        if (!el) return false;

        // 1. Exact name match
        if (el.getAttribute('name') === identifier) return true;

        // 2. ID match
        if (el.id === identifier) return true;

        // 3. Placeholder match (exact then partial)
        var ph = el.getAttribute('placeholder');
        if (ph) {
            var phLower = ph.toLowerCase().trim();
            if (phLower === lowerIdentifier || phLower.includes(lowerIdentifier)) return true;
        }

        // 4. ARIA label
        var ariaLabel = el.getAttribute('aria-label');
        if (ariaLabel && ariaLabel.toLowerCase().includes(lowerIdentifier)) return true;

        // 5. ARIA labelledby
        var labelledBy = el.getAttribute('aria-labelledby');
        if (labelledBy) {
            var labelEl = document.getElementById(labelledBy);
            if (labelEl) {
                var labelContent = labelEl.innerText || labelEl.textContent || "";
                if (labelContent.toLowerCase().includes(lowerIdentifier)) return true;
            }
        }

        return false;
    }

    // List of form-friendly elements
    var selectors = 'input, textarea, select, button, ' +
        '[role="button"], [role="textbox"], [role="checkbox"], [role="radio"]';
    var forms = document.querySelectorAll(selectors);
    for (var i = 0; i < forms.length; i++) {
        if (elementMatches(forms[i])) return forms[i];
    }

    // Check labels
    var labels = document.querySelectorAll('label');
    for (var i = 0; i < labels.length; i++) {
        var labelText = (labels[i].innerText || labels[i].textContent || "").toLowerCase();
        if (labelText.includes(lowerIdentifier)) {
            var forAttr = labels[i].getAttribute('for');
            if (forAttr) {
                var el = document.getElementById(forAttr);
                if (el) return el;
            }
            // Nested input
            var inner = labels[i].querySelector('input, textarea, select, button');
            if (inner) return inner;
        }
    }

    return null;
})();
"""


# NOTE: This is a module-level constant. DO NOT mutate.
_FILL_FORM_JS = """
(function() {
    var label = '{label}';
    var value = '{value}';
    // Try by label
    var labels = document.querySelectorAll('label');
    for (var i = 0; i < labels.length; i++) {
        if (labels[i].innerText.includes(label)) {
            var forAttr = labels[i].getAttribute('for');
            var input;
            if (forAttr) {
                input = document.getElementById(forAttr);
            } else {
                input = labels[i].querySelector('input, textarea');
            }
            if (input) {
                input.value = value;
                input.dispatchEvent(new Event('input', {bubbles: true}));
                input.dispatchEvent(new Event('change', {bubbles: true}));
                return true;
            }
        }
    }
    // Try by name/id
    var input = document.querySelector(
        '[name="' + label + '"], #' + label
    );
    if (input) {
        input.value = value;
        input.dispatchEvent(new Event('input', {bubbles: true}));
        input.dispatchEvent(new Event('change', {bubbles: true}));
        return true;
    }
    return false;
})();
"""


class Browser:
    """
    Hybrid browser automation using Chrome DevTools.

    Connects to your existing Chrome (requires --remote-debugging-port=9222).
    For authenticated sessions, just use your normal Chrome login.

    Uses a connection pool for WebSocket reuse across operations.

    Note: HTTP operations (tab management) use synchronous urllib.request.
    In async contexts, these will block the event loop briefly.
    For heavy async use, consider running in a separate thread.

    Recommended usage:
        with Browser() as b:
            b.goto("...")
            ...

    Or explicit cleanup:
        b = Browser()
        try:
            ...
        finally:
            b.close()

    Launching Chrome:
        # Option 1: Use existing Chrome instance
        b = Browser(host="localhost", port=9222)

        # Option 2: Launch Chrome with Browser.launch()
        b = Browser.launch(headless=True, stealth=True, block_trackers=True)
        b.goto("https://example.com")
        await b.close()
    """

    @staticmethod
    def launch(
        headless: bool = True,
        stealth: bool = True,
        stealth_mode: str = "basic",
        block_trackers: bool = True,
        port: int = 9222,
        user_data_dir: str | None = None,
        profile_path: str | None = None,
    ) -> Browser:
        """
        Launch Chrome and create a Browser instance.

        Convenience method that launches Chrome with appropriate flags
        and returns a connected Browser instance.

        Args:
            headless: Run Chrome in headless mode (default: True)
            stealth: Enable stealth mode (hides automation signals, default: True)
            stealth_mode: Stealth mode level ("basic", "balanced", "aggressive", default: "basic")
            block_trackers: Block known tracking/bot detection domains (default: True)
            port: Remote debugging port (default: 9222)
            user_data_dir: User data directory (None = temp profile, deprecated: use profile_path)
            profile_path: Persistent profile directory path (None = temp profile, default: None)

        Returns:
            Browser instance connected to the launched Chrome

        Raises:
            FileNotFoundError: If Chrome is not found
            RuntimeError: If Chrome fails to start
            ValueError: If invalid stealth_mode is provided

        Example:
            # Launch Chrome with stealth and tracker blocking
            b = Browser.launch(headless=True, stealth=True, block_trackers=True)
            b.goto("https://example.com")
            await b.close()

            # Launch Chrome with aggressive stealth
            b = Browser.launch(headless=True, stealth=True, stealth_mode="aggressive")
            b.goto("https://example.com")
            await b.close()

            # Launch Chrome with persistent profile
            b = Browser.launch(headless=True, profile_path="/tmp/my-browser-profile")
            b.goto("https://gmail.com")
            await b.close()

            # Launch Chrome with visible window and authenticated session
            b = Browser.launch(headless=False, profile_path="/Users/burnz/.config/google-chrome/Default")
            b.goto("https://gmail.com")
            await b.close()
        """
        if stealth_mode not in ["basic", "balanced", "aggressive"]:
            raise ValueError(
                f"Invalid stealth_mode: {stealth_mode}. "
                f"Must be one of: 'basic', 'balanced', 'aggressive'"
            )
        # Map profile_path to user_data_dir (profile_path is the public API)
        effective_user_data_dir = profile_path or user_data_dir

        # Launch Chrome
        chrome_path, remote_url = _launch_chrome(
            headless=headless,
            stealth=stealth,
            block_trackers=block_trackers,
            port=port,
            user_data_dir=effective_user_data_dir,
        )

        # Parse host and port from URL
        parsed = urllib.parse.urlparse(remote_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 9222

        # Create Browser instance
        browser = Browser(
            host=host,
            port=port,
            stealth=stealth,
            stealth_mode=stealth_mode,
            block_trackers=block_trackers,
            profile_path=effective_user_data_dir,
        )

        # Set _current_tab to the first available tab
        tabs = browser.list_tabs()
        if tabs:
            browser._current_tab = tabs[0]

        logger.info(
            "Browser launched via Browser.launch() - "
            "headless=%s, stealth=%s, block_trackers=%s",
            headless,
            stealth,
            block_trackers,
        )

        return browser

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT,
        retry_attempts: int = 0,
        retry_delay: float = 1.0,
        pool_rate_limit: float | None = None,
        cache_accessibility: bool = False,
        reconnect: bool = True,
        reconnect_max_retries: int = 3,
        reconnect_backoff: float = 1.0,
        reconnect_callback: Callable[[str], None] | None = None,
        stealth: bool = False,
        stealth_mode: str = "basic",
        block_trackers: bool = False,
        profile_path: str | None = None,
    ):
        """
        Initialize browser connection.

        Note: Only tabs within a single Chrome window are supported.
        Use Chrome with --new-window or ensure all tabs are in one window.

        Examples:
            # Disable auto-reconnect:
            browser = Browser(reconnect=False)

            # Enable stealth mode (basic):
            browser = Browser(stealth=True)

            # Enable stealth mode (aggressive):
            browser = Browser(stealth=True, stealth_mode="aggressive")

            # Block known tracking/bot detection domains:
            browser = Browser(block_trackers=True)

            # Use persistent profile:
            browser = Browser(profile_path="/tmp/my-browser-profile")

            # Monitor reconnection:
            def on_reconnect(msg):
                print(f"Reconnecting: {msg}")
            browser = Browser(reconnect_callback=on_reconnect)

        Args:
            host: Chrome DevTools host (default: localhost)
            port: Chrome DevTools port (default: 9222)
            timeout: Default timeout for operations (default: 10.0 seconds)
            retry_attempts: Number of times to retry initial connection
            retry_delay: Delay between retries in seconds
            pool_rate_limit: Minimum seconds between CDP calls (rate limiting)
            cache_accessibility: Enable caching of accessibility trees (default: False)
            reconnect: Enable automatic reconnection (default: True)
            reconnect_max_retries: Maximum reconnection attempts (default: 3)
            reconnect_backoff: Base backoff time for reconnection (default: 1.0s)
            reconnect_callback: Called with status messages during reconnect
            stealth: Enable stealth mode (hides automation signals, default: False)
            stealth_mode: Stealth mode level ("basic", "balanced", "aggressive", default: "basic")
            block_trackers: Block known tracking/bot detection domains (default: False)
            profile_path: Persistent profile directory path (None = temp profile, default: None)

        Raises:
            ConnectionError: If Chrome DevTools is not reachable
            ValueError: If invalid stealth_mode is provided
        """
        if stealth_mode not in ["basic", "balanced", "aggressive"]:
            raise ValueError(
                f"Invalid stealth_mode: {stealth_mode}. "
                f"Must be one of: 'basic', 'balanced', 'aggressive'"
            )
        self.host = host
        self.port = port
        self.timeout = timeout
        self.pool_rate_limit = pool_rate_limit
        self.cache_accessibility = cache_accessibility
        self.reconnect_enabled = reconnect
        self.reconnect_max_retries = reconnect_max_retries
        self.reconnect_backoff = reconnect_backoff
        self.reconnect_callback = reconnect_callback
        self._interceptors: dict[str, list[Callable[[dict], None]]] = {}
        self._interceptor_filters: dict[str, dict] = {}
        self._accessibility_cache: dict[str, AXNode] = {}
        self._reconnect_tasks: set[asyncio.Task[Any]] = set()
        self.base_url = f"http://{host}:{port}"
        self._current_tab: Tab | None = None
        self._pool: ConnectionPool | None = None
        self._block_trackers = block_trackers
        self._blocked_urls: set[str] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_lock = threading.Lock()
        self._recording: Recording | None = None
        self._playing_back: bool = False
        self._record_depth: contextvars.ContextVar[int] = contextvars.ContextVar(
            "record_depth", default=0
        )
        self._stealth = stealth
        self._stealth_mode: str = stealth_mode
        self._stealth_script: str | None = None
        self._profile_path: str | None = profile_path

        # Check connection with optional retries
        if not self._check_connection():
            connected = False
            if retry_attempts > 0:
                for _ in range(retry_attempts):
                    time.sleep(retry_delay)
                    if self._check_connection():
                        connected = True
                        break

            if not connected:
                raise ConnectionError(
                    f"Chrome DevTools not reachable at {self.base_url}",
                    host=host,
                    port=port,
                )

        # Register cleanup on program exit
        atexit.register(self._cleanup)

    # ─────────────────────────────────────────────────────────────────────────────
    # Connection Management
    # ─────────────────────────────────────────────────────────────────────────────

    def _check_connection(self) -> bool:
        """Check if Chrome DevTools is reachable."""
        try:
            urllib.request.urlopen(f"{self.base_url}/json/version", timeout=2)
            return True
        except (urllib.error.URLError, urllib.error.HTTPError):
            return False

    def _get_pool(self) -> ConnectionPool:
        """Get or create connection pool (thread-safe)."""
        # Double-checked locking pattern
        if self._pool is None:
            with self._loop_lock:
                if self._pool is None:
                    self._pool = ConnectionPool(
                        timeout=self.timeout, rate_limit=self.pool_rate_limit
                    )
        return self._pool

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create shared event loop (thread-safe)."""
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            with self._loop_lock:
                if self._loop is None or self._loop.is_closed():
                    self._loop = asyncio.new_event_loop()
                return self._loop

    def _run_async(self, coro: Any) -> Any:
        """Run coroutine on shared event loop."""
        loop = self._get_loop()
        if threading.current_thread() is threading.main_thread():
            if loop.is_running():
                # Cannot block if the loop is already running in this thread
                # This happens during async tests or if called from a callback
                return loop.create_task(coro)
            return loop.run_until_complete(coro)
        else:
            # Thread-safe execution
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result()

    def _resolve_tab(self, tab: Tab | str | None) -> Tab | None:
        """Resolve Tab | str | None to Tab | None."""
        if tab is None:
            return None
        if isinstance(tab, Tab):
            return tab
        # tab is str - lookup Tab object
        tabs = self.list_tabs()
        for t in tabs:
            if t.id == tab:
                return t
        return None

    async def _get_connection(self, tab: Tab | None = None) -> Connection:
        """Get WebSocket connection for a tab."""
        tab_to_use = tab or self._get_current_tab()
        pool = self._get_pool()
        conn = await pool.get_connection(
            tab_to_use.id,
            tab_to_use.web_socket_debugger_url,
        )

        # Set up auto-reconnect if enabled
        if self.reconnect_enabled and not conn.on_state_change:
            from .connection import ConnectionState

            def handle_state_change(state: ConnectionState):
                if state == ConnectionState.DISCONNECTED:
                    # Connection dropped - trigger re-connection task
                    loop = asyncio.get_running_loop()
                    task = loop.create_task(self._handle_disconnect(conn))
                    self._reconnect_tasks.add(task)
                    task.add_done_callback(self._reconnect_tasks.discard)

            conn.on_state_change = handle_state_change

        return conn

    async def _handle_disconnect(self, conn: Connection) -> None:
        """Handle connection disconnect event by attempting reconnect."""
        if not self.reconnect_enabled:
            return

        try:
            msg = f"Connection to tab {conn.tab_id} lost. Attempting automatic reconnection..."
            logger.info(msg)
            if self.reconnect_callback:
                self.reconnect_callback(msg)

            success = await conn.reconnect(
                max_retries=self.reconnect_max_retries,
                base_backoff=self.reconnect_backoff,
            )
            if success:
                msg = f"Automatic reconnection to tab {conn.tab_id} successful."
                logger.info(msg)
                if self.reconnect_callback:
                    self.reconnect_callback(msg)
                await self._reregister_interceptors(conn)
            else:
                msg = (
                    f"Automatic reconnection to tab {conn.tab_id} failed "
                    f"after {self.reconnect_max_retries} attempts."
                )
                logger.warning(msg)
                if self.reconnect_callback:
                    self.reconnect_callback(msg)
        except asyncio.CancelledError:
            # Task was cancelled during cleanup - exit cleanly
            logger.debug("Reconnection task cancelled")
        except Exception as e:
            logger.error(f"Error during automatic reconnection: {e}")

    def _resolve_timeout(self, timeout: float | None) -> float:
        """Resolve timeout parameter, treating None as 'use default'."""
        return timeout if timeout is not None else self.timeout

    def is_connected(self) -> bool:
        """Check if Chrome is reachable."""
        return self._check_connection()

    def wait_for_chrome(self, timeout: float = 30.0) -> bool:
        """
        Wait for Chrome to become available.

        This is a synchronous method and will block the event loop.
        Use wait_for_chrome_async() for async contexts.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            True if Chrome became available, False if timeout
        """
        start = time.time()
        while time.time() - start <= timeout:
            if self._check_connection():
                return True
            time.sleep(0.5)
        return False

    async def wait_for_chrome_async(self, timeout: float = 30.0) -> bool:
        """
        Wait for Chrome to become available (async version).

        This is an asynchronous method and will not block the event loop.

        Args:
            timeout: Maximum seconds to wait

        Returns:
            True if Chrome became available, False if timeout
        """
        start = time.time()
        while time.time() - start <= timeout:
            if self._check_connection():
                return True
            await asyncio.sleep(0.5)
        return False

    @property
    def current_tab(self) -> Tab | None:
        """Get the current active tab."""
        return self._current_tab

    @current_tab.setter
    def current_tab(self, tab: Tab | None) -> None:
        """Set the current active tab."""
        self._current_tab = tab

    # ─────────────────────────────────────────────────────────────────────────────
    # HTTP API (Tab Management)
    # ─────────────────────────────────────────────────────────────────────────────

    def _http_get(self, path: str, timeout: float | None = None) -> Any:
        """
        HTTP GET to Chrome DevTools.

        Note: This is a synchronous HTTP call that blocks.
        """
        url = f"{self.base_url}{path}"
        timeout_val = self._resolve_timeout(timeout)
        try:
            with urllib.request.urlopen(url, timeout=timeout_val) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            raise BrowserError(f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise ConnectionError(
                "Failed to connect",
                host=self.host,
                port=self.port,
                original_error=e,
            )

    def _http_put(self, path: str, timeout: float | None = None) -> dict[str, Any]:
        """
        HTTP PUT to Chrome DevTools.

        Note: This is a synchronous HTTP call that blocks.
        """
        url = f"{self.base_url}{path}"
        timeout_val = self._resolve_timeout(timeout)
        req = urllib.request.Request(url, method="PUT")
        try:
            with urllib.request.urlopen(req, timeout=timeout_val) as response:
                data = response.read().decode()
                if not data:
                    return {"success": True}
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    return {"result": data.strip()}
        except urllib.error.HTTPError as e:
            if e.code in (200, 204):
                return {"success": True}
            logger.warning(f"HTTP PUT failed: {e.code} {e.reason} for {url}")
            raise BrowserError(f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            logger.warning(f"URL error: {e.reason} for {url}")
            raise ConnectionError(
                "Failed to connect",
                host=self.host,
                port=self.port,
                original_error=e,
            )
        except Exception as e:
            logger.error(f"Unexpected error in _http_put: {e}")
            raise BrowserError(f"Unexpected HTTP error: {str(e)}")

    def list_tabs(self) -> list[Tab]:
        """List all open tabs."""
        data = self._http_get("/json/list")
        return [Tab.from_dict(t) for t in data if t.get("type") == "page"]

    def new_tab(self, url: str = "about:blank") -> Tab:
        """Open a new tab with URL.

        Uses two-step process for reliability:
        1. Create empty tab via /json/new
        2. Navigate via CDP Page.navigate if URL provided

        This is more reliable than /json/new?url= which may not
        properly wait for navigation in some environments.

        Note:
            If stealth mode is enabled, anti-detection scripts are injected
            synchronously before navigation starts. This ensures all signals
            (navigator.webdriver, chrome.runtime, cdc_*, puppeteer) are hidden
            before any page JavaScript executes.
            
            If a URL is provided, navigation starts but does NOT wait for it to complete.
            The tab object is returned immediately after navigation begins.
            Use `goto()` if you need to wait for the page to fully load.
        """
        # Create empty tab
        data = self._http_put("/json/new")
        tab = Tab.from_dict(data)
        self._current_tab = tab

        # Inject stealth script if enabled
        if self._stealth:
            try:
                # Wait for stealth injection to complete before navigating
                result = self._run_async(self._inject_stealth_script(tab))
                if hasattr(result, "result"):
                    result.result(timeout=5.0)
            except RuntimeError:
                # Event loop not running, skip injection
                pass
            except Exception as e:
                logger.warning("Stealth script injection failed: %s", e)

        # Set up tracker blocklist if enabled
        if self._block_trackers:
            try:
                # Wait for blocklist setup to complete
                result = self._run_async(self._setup_tracker_blocklist(tab))
                if hasattr(result, "result"):
                    result.result(timeout=5.0)
            except RuntimeError:
                # Event loop not running, skip blocklist setup
                pass
            except Exception as e:
                logger.warning("Tracker blocklist setup failed: %s", e)

        # Navigate if URL provided (not about:blank)
        if url and url != "about:blank":
            self.navigate(url, tab=tab)

        return tab

    def activate_tab(self, tab_id: str) -> bool:
        """Bring tab to front (focus)."""
        self._http_put(f"/json/activate/{tab_id}")
        return True

    def close_tab(self, tab: Tab | str | None = None) -> bool:
        """
        Close a tab.

        Args:
            tab: Tab object, tab ID string, or None to close current tab

        Returns:
            True if closed successfully
        """
        # Accept both Tab object and string ID
        tab_id: str | None
        if tab is None and self._current_tab:
            tab_id = self._current_tab.id
        elif isinstance(tab, Tab):
            tab_id = tab.id
        else:
            tab_id = tab
        if tab_id:
            self._http_put(f"/json/close/{tab_id}")
            # Remove from connection pool
            if self._pool:
                self._run_async(self._pool.remove(tab_id))

            # Update _current_tab if we closed the current tab
            if self._current_tab and self._current_tab.id == tab_id:
                tabs = self.list_tabs()
                self._current_tab = tabs[0] if tabs else None

            return True
        return False

    def get_version(self) -> BrowserInfo:
        """Get Chrome version info."""
        data = self._http_get("/json/version")
        return BrowserInfo.from_dict(data)

    @contextmanager
    def temp_tab(self, url: str = "about:blank", close_on_exit: bool = True):
        """
        Create a temporary tab for isolated workflow.

        Args:
            url: Initial URL to navigate to
            close_on_exit: Close tab when context exits (default: True)

        Returns:
            Context manager yielding Tab
        """
        from contextlib import suppress

        tab = self.new_tab(url)
        try:
            yield tab
        finally:
            if close_on_exit:
                with suppress(Exception):
                    self.close_tab(tab)

    def switch_to_tab(self, tab: Tab | str, focus: bool = True) -> Tab | None:
        """
        Switch to a specific tab, optionally focusing browser window.

        Args:
            tab: Tab object or ID to switch to
            focus: Also bring Chrome window to foreground (default: True)

        Returns:
            Previous tab (for switching back)
        """
        prev = self.current_tab
        tab_id = tab.id if isinstance(tab, Tab) else tab

        if focus:
            self.activate_tab(tab_id)

        # Update current tab tracking
        if isinstance(tab, Tab):
            self.current_tab = tab
        else:
            # Re-fetch from list to get full Tab object
            tabs = self.list_tabs()
            for t in tabs:
                if t.id == tab_id:
                    self.current_tab = t
                    break

        return prev

    # ─────────────────────────────────────────────────────────────────────────────
    # WebSocket CDP Commands
    # ─────────────────────────────────────────────────────────────────────────────

    async def _send_cdp(
        self,
        conn: Connection,
        method: str,
        params: dict[str, Any] | None = None,
        domains: list[str] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        Send CDP command via connection.

        Handles domain enabling and error parsing.
        """
        # Enable domains if needed
        if domains:
            for domain in domains:
                enable_res = await conn.send(f"{domain}.enable", timeout=timeout)
                if error := parse_cdp_error(enable_res, f"{domain}.enable"):
                    raise error

        # Send command
        if self.reconnect_enabled and conn.state == ConnectionState.DISCONNECTED:
            msg = (
                f"Connection to tab {conn.tab_id} disconnected. "
                f"Reconnecting before command '{method}'..."
            )
            logger.info(msg)
            if self.reconnect_callback:
                self.reconnect_callback(msg)

            success = await conn.reconnect(
                max_retries=self.reconnect_max_retries,
                base_backoff=self.reconnect_backoff,
            )
            if not success:
                msg = (
                    f"Failed to reconnect to tab {conn.tab_id} for command '{method}'."
                )
                logger.error(msg)
                if self.reconnect_callback:
                    self.reconnect_callback(msg)
                raise ConnectionError(
                    msg, original_error=conn.last_error
                ) from conn.last_error

            msg = f"Reconnected to tab {conn.tab_id} for command '{method}'."
            logger.info(msg)
            if self.reconnect_callback:
                self.reconnect_callback(msg)
            await self._reregister_interceptors(conn)

        result = await conn.send(method, params, timeout=timeout)
        if error := parse_cdp_error(result, method):
            raise error

        return result.get("result", result)

    def _get_current_tab(self) -> Tab:
        """Get current tab or raise error."""
        if self._current_tab:
            return self._current_tab
        tabs = self.list_tabs()
        if tabs:
            self._current_tab = tabs[0]
            return tabs[0]
        raise TabError("No tab available. Call new_tab() first.")

    # ─────────────────────────────────────────────────────────────────────────────
    # Session Recording & Playback
    # ─────────────────────────────────────────────────────────────────────────────

    def start_recording(self, path: str | None = None) -> Recording:
        """
        Start recording browser actions.

        Args:
            path: Optional path to save recording (default: temp file)

        Returns:
            Recording object for control
        """
        self._recording = Recording(
            path=path,
            quay_version=__version__,
            recorded_at=datetime.datetime.now().isoformat(),
            start_time=time.time(),
        )
        logger.info(f"Recording started. Output: {path or 'Temporary file'}")
        return self._recording

    def stop_recording(self) -> str:
        """
        Stop recording and save to file.

        Returns:
            Path to saved recording file

        Raises:
            ValueError: If no recording in progress
        """
        if not self._recording:
            raise ValueError("No recording in progress")

        self._recording.end_time = time.time()
        recording = self._recording
        self._recording = None

        # Save to file
        path = recording.save()
        logger.info(f"Recording saved to: {path}")
        return path

    def pause_recording(self) -> None:
        """Pause recording."""
        if self._recording:
            self._recording.paused = True

    def resume_recording(self) -> None:
        """Resume recording."""
        if self._recording:
            self._recording.paused = False

    def get_recording(self) -> Recording | None:
        """Get current recording session."""
        return self._recording

    def _record_action(self, action_type: str, **params) -> None:
        """Record an action with current timestamp."""
        if (
            not self._recording
            or self._recording.paused
            or self._playing_back
            or self._record_depth.get() > 0
        ):
            return

        if self._recording.start_time is None:
            return

        elapsed = time.time() - self._recording.start_time
        action = Action(type=action_type, timestamp=elapsed, params=params)
        self._recording.actions.append(action)

    def playback(
        self, recording: Recording | str, speed: float = 1.0, verify: bool = False
    ) -> bool:
        """
        Replay recorded browser actions.

        Args:
            recording: Recording object or path to JSON file
            speed: Playback speed multiplier (default: 1.0)
            verify: Raise BrowserError if actions fail (default: False)

        Returns:
            True if playback completed successfully
        """
        if isinstance(recording, str):
            if not os.path.exists(recording):
                raise FileNotFoundError(f"Recording file not found: {recording}")
            with open(recording) as f:
                data = json.load(f)
                recording = Recording.from_dict(data)

        if not isinstance(recording, Recording):
            raise TypeError("Expected Recording object or JSON file path")

        logger.info(
            f"Starting playback: {len(recording.actions)} actions (speed: {speed}x)"
        )

        self._playing_back = True
        try:
            last_ts = 0.0
            for action in recording.actions:
                # Wait for timing (timestamp is from start of recording)
                delay = (action.timestamp - last_ts) / speed
                if delay > 0:
                    time.sleep(delay)
                last_ts = action.timestamp

                # Execute action
                logger.info(f"Playback action: {action.type}({action.params})")
                try:
                    method = getattr(self, action.type)
                    result = method(**action.params)

                    # For actions that return bool (click, type, wait_for),
                    # check success if verify=True
                    if verify and result is False:
                        raise BrowserError(
                            f"Action '{action.type}' failed during playback (returned False)"
                        )
                except Exception as e:
                    logger.error(f"Playback failed for action {action.type}: {e}")
                    if verify:
                        if not isinstance(e, BrowserError):
                            raise BrowserError(
                                f"Playback failed at {action.type}: {e}"
                            ) from e
                        raise e
            return True
        finally:
            self._playing_back = False

    # ─────────────────────────────────────────────────────────────────────────────
    # Stealth Mode
    # ─────────────────────────────────────────────────────────────────────────────

    async def _inject_stealth_script(self, tab: Tab) -> bool:
        """
        Inject stealth script to hide automation signals.

        Args:
            tab: Tab to inject script into

        Returns:
            True if injection succeeded
        """
        if not self._stealth:
            return True

        # Initialize script if not already done
        if self._stealth_script is None:
            # Select script based on stealth_mode
            if self._stealth_mode == "basic":
                self._stealth_script = _STEALTH_SCRIPT_BASIC
            elif self._stealth_mode == "balanced":
                self._stealth_script = _STEALTH_SCRIPT_BALANCED
            elif self._stealth_mode == "aggressive":
                self._stealth_script = _STEALTH_SCRIPT_AGGRESSIVE
            else:
                self._stealth_script = _STEALTH_SCRIPT_BASIC

        try:
            # Get connection for this tab
            conn = await self._get_connection(tab)

            # Inject script on page lifecycle init (before any JS runs)
            result = await conn.send(
                "Page.addScriptToEvaluateOnNewDocument",
                params={"source": self._stealth_script},
            )

            if error := parse_cdp_error(result, "Page.addScriptToEvaluateOnNewDocument"):
                logger.warning("Stealth script injection failed: %s", error.message)
                return False

            return True
        except Exception as e:
            logger.warning("Stealth script injection error: %s", e)
            return False

    # ─────────────────────────────────────────────────────────────────────────────
    # Tracker Blocking
    # ─────────────────────────────────────────────────────────────────────────────

    async def _setup_tracker_blocklist(self, tab: Tab) -> bool:
        """
        Set up CDP network interception to block known tracking/bot detection domains.

        Args:
            tab: Tab to block trackers on

        Returns:
            True if setup succeeded
        """
        if not self._block_trackers:
            return True

        try:
            conn = await self._get_connection(tab)

            # Enable Network domain for interception
            await conn.send("Network.enable")

            # Build patterns for blocking — CDP needs one pattern per entry
            blocked_patterns = [
                {"urlPattern": f"*{domain}*"} for domain in _BLOCKLIST
            ]

            # Set up request interception
            result = await conn.send(
                "Network.setRequestInterception",
                params={"patterns": blocked_patterns},
            )

            if error := parse_cdp_error(result, "Network.setRequestInterception"):
                logger.warning("Tracker blocklist setup failed: %s", error.message)
                return False

            # Register callback for intercepted requests
            def on_intercepted_request(params: dict) -> None:
                interception_id = params.get("interceptionId")
                url = params.get("request", {}).get("url", "")
                if interception_id and url:
                    # Handle in background (don't block the event)
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(self._handle_blocked_request(tab, interception_id, url))
                    except RuntimeError:
                        # No running loop, skip
                        pass

            conn.on_event("Network.requestIntercepted", on_intercepted_request)

            logger.info("Tracker blocking enabled for %d domains", len(_BLOCKLIST))
            return True
        except Exception as e:
            logger.warning("Tracker blocklist setup error: %s", e)
            return False

    async def _handle_blocked_request(self, tab: Tab, interception_id: str, url: str) -> bool:
        """
        Handle a network request intercepted by CDP.

        Blocks requests matching tracker domains, continues others.

        Args:
            tab: Tab the request is for
            interception_id: CDP interception ID (from Network.requestIntercepted)
            url: Request URL

        Returns:
            True if request was blocked
        """
        # Check if URL matches any blocked domain
        for domain in _BLOCKLIST:
            if domain in url:
                try:
                    conn = await self._get_connection(tab)
                    # Abort the request
                    await conn.send(
                        "Network.abortRequest",
                        params={"interceptionId": interception_id},
                    )
                    logger.debug("Blocked tracker: %s", url)
                    return True
                except Exception as e:
                    logger.warning("Failed to abort request %s: %s", interception_id, e)
                    return False

        # Continue non-blocked requests
        try:
            conn = await self._get_connection(tab)
            await conn.send(
                "Network.continueRequest",
                params={"interceptionId": interception_id},
            )
            return False
        except Exception as e:
            logger.warning("Failed to continue request %s: %s", interception_id, e)
            return False

    # ─────────────────────────────────────────────────────────────────────────────
    # Navigation
    # ─────────────────────────────────────────────────────────────────────────────

    def navigate(
        self,
        url: str,
        tab: Tab | None = None,
        timeout: float | None = None,
    ) -> str:
        """
        Navigate tab to URL.

        Args:
            url: URL to navigate to
            tab: Tab to navigate (defaults to current)
            timeout: Operation timeout

        Returns:
            Frame ID

        Note:
            This method fires the navigation and returns immediately.
            Use `goto()` if you need to wait for the page to fully load.
        """
        self._record_action("navigate", url=url)
        token = self._record_depth.set(self._record_depth.get() + 1)

        async def _navigate():
            try:
                conn = await self._get_connection(tab)
                result = await self._send_cdp(
                    conn,
                    "Page.navigate",
                    {"url": url},
                    domains=["Page"],
                    timeout=timeout,
                )
                # Refresh tab metadata after navigation
                if tab:
                    title_result = await self._send_cdp(
                        conn,
                        "Runtime.evaluate",
                        {"expression": "document.title", "returnByValue": True},
                        timeout=timeout,
                    )
                    url_result = await self._send_cdp(
                        conn,
                        "Runtime.evaluate",
                        {"expression": "document.URL", "returnByValue": True},
                        timeout=timeout,
                    )
                    if title_result:
                        tab.title = (
                            title_result.get("result", {}).get("value", tab.title)
                            or tab.title
                        )
                    if url_result:
                        tab.url = (
                            url_result.get("result", {}).get("value", tab.url)
                            or tab.url
                        )
                return result.get("frameId", "")
            finally:
                pass

        try:
            return self._run_async(_navigate())
        finally:
            self._record_depth.reset(token)

    def goto(
        self,
        url: str,
        timeout: float | None = None,
        page_load_timeout: float | None = None,
    ) -> Tab:
        """
        Create a new tab, navigate to URL, and wait for load.

        This is a convenience method that combines:
        1. `new_tab(url)` - create tab and start navigation
        2. `wait_for_load_state()` - wait for page to reach 'load' state

        Args:
            url: URL to navigate to
            timeout: CDP operation timeout (default 30s)
            page_load_timeout: Max time for page to reach 'load'
                             (default: uses timeout parameter)

        Returns:
            Tab object (the newly created tab)

        Note:
            Unlike `navigate()`, this method creates a new tab and waits for the page to load.
            Use this when you want to ensure the page is fully loaded before proceeding.
        """
        self._record_action(
            "goto", url=url, timeout=timeout, page_load_timeout=page_load_timeout
        )
        token = self._record_depth.set(self._record_depth.get() + 1)

        # Resolve timeouts
        cdp_timeout = self._resolve_timeout(timeout)
        load_timeout = (
            page_load_timeout if page_load_timeout is not None else cdp_timeout
        )

        try:
            tab = self.new_tab(url)
            try:
                self.wait_for_load_state(tab=tab, timeout=load_timeout)
            except TimeoutError:
                # Fallback if load state not reachable - page might still be usable
                pass
            return tab
        finally:
            self._record_depth.reset(token)

    def wait_for_load_state(
        self, state: str = "load", tab: Tab | str | None = None, timeout: float = 30.0
    ) -> bool:
        """
        Wait until the page reaches a specific load state.

        Args:
            state: Load state ('load' or 'DOMContentLoaded')
            tab: Tab to wait for (defaults to current, accepts Tab, tab ID, or None)
            timeout: Maximum wait time

        Returns:
            True if state reached
        """
        self._record_action("wait_for_load_state", state=state, timeout=timeout)
        token = self._record_depth.set(self._record_depth.get() + 1)
        resolved_tab = self._resolve_tab(tab)

        async def _wait() -> bool:
            try:
                conn = await self._get_connection(resolved_tab)

                start_time = asyncio.get_event_loop().time()
                interval = 0.1
                while asyncio.get_event_loop().time() - start_time < timeout:
                    try:
                        result = await self._send_cdp(
                            conn,
                            "Runtime.evaluate",
                            {
                                "expression": "document.readyState",
                                "returnByValue": True,
                            },
                            domains=["Runtime"],
                        )
                        ready_state = result.get("result", {}).get("value")

                        if state == "load" and ready_state == "complete":
                            return True
                        if state == "DOMContentLoaded" and ready_state in [
                            "interactive",
                            "complete",
                        ]:
                            return True
                    except Exception:
                        # Connection might be busy or page not ready for JS yet
                        pass

                    await asyncio.sleep(interval)

                raise TimeoutError(
                    f"Wait for load state '{state}' timed out after {timeout}s",
                    timeout=timeout,
                    operation="wait_for_load_state",
                )
            finally:
                pass

        try:
            return self._run_async(_wait())
        finally:
            self._record_depth.reset(token)

    def wait_for(
        self,
        selector: str | None = None,
        text: str | None = None,
        tab: Tab | str | None = None,
        timeout: float = 30.0,
    ) -> bool:
        """
        Wait for element or text to appear.

        Args:
            selector: CSS selector to wait for
            text: Text content to wait for
            tab: Tab to wait on (defaults to current)
            timeout: Maximum seconds to wait

        Returns:
            True if found, False if timeout
        """
        self._record_action(
            "wait_for", selector=selector, text=text, tab=tab, timeout=timeout
        )
        token = self._record_depth.set(self._record_depth.get() + 1)
        resolved_tab = self._resolve_tab(tab)
        try:
            start = time.time()
            while time.time() - start <= timeout:
                if selector:
                    escaped_selector = escape_js_string(selector)
                    try:
                        result = self.evaluate(
                            f"document.querySelector('{escaped_selector}') !== null",
                            tab=resolved_tab,
                        )
                        if result:
                            return True
                    except (ConnectionError, TimeoutError, BrowserError):
                        pass  # Transient error, retry
                if text:
                    escaped_text = escape_js_string(text)
                    try:
                        result = self.evaluate(
                            f"document.body.innerText.includes('{escaped_text}')",
                            tab=resolved_tab,
                        )
                        if result:
                            return True
                    except (ConnectionError, TimeoutError, BrowserError):
                        pass  # Transient error, retry
                time.sleep(0.2)
            return False
        finally:
            self._record_depth.reset(token)

    def wait_for_url(
        self,
        url: str | None = None,
        pattern: str | None = None,
        tab: Tab | str | None = None,
        timeout: float = 30.0,
    ) -> bool:
        """
        Wait for page URL to match.

        Args:
            url: Exact URL to wait for
            pattern: Regex pattern to match URL against
            tab: Tab to wait on (defaults to current)
            timeout: Maximum seconds to wait

        Returns:
            True if URL matched, False if timeout

        Note: Either url or pattern must be provided, not both.
        """
        self._record_action(
            "wait_for_url", url=url, pattern=pattern, tab=tab, timeout=timeout
        )
        token = self._record_depth.set(self._record_depth.get() + 1)
        resolved_tab = self._resolve_tab(tab)
        try:
            if url and pattern:
                raise ValueError("Provide either url or pattern, not both")
            if not url and not pattern:
                raise ValueError("Either url or pattern must be provided")

            # Compile pattern once outside the loop
            import re

            compiled_pattern = re.compile(pattern) if pattern else None

            start = time.time()
            while time.time() - start <= timeout:
                try:
                    current_url = self.evaluate(
                        "window.location.href", tab=resolved_tab
                    )
                    if url and current_url == url:
                        return True
                    if compiled_pattern and compiled_pattern.search(current_url):
                        return True
                except (ConnectionError, TimeoutError, BrowserError):
                    pass  # Transient error, retry
                time.sleep(0.2)
            return False
        finally:
            self._record_depth.reset(token)

    def wait_for_selector_visible(
        self,
        selector: str,
        timeout: float = 30.0,
    ) -> bool:
        """
        Wait for element to be visible (displayed and not hidden).

        Args:
            selector: CSS selector
            timeout: Maximum seconds to wait

        Returns:
            True if element became visible, False if timeout
        """
        self._record_action(
            "wait_for_selector_visible", selector=selector, timeout=timeout
        )
        token = self._record_depth.set(self._record_depth.get() + 1)
        try:
            escaped = escape_js_string(selector)
            start = time.time()
            while time.time() - start <= timeout:
                try:
                    visible = self.evaluate(
                        f"(function() {{"
                        f"  const el = document.querySelector('{escaped}');"
                        f"  if (!el) return false;"
                        f"  const style = window.getComputedStyle(el);"
                        f"  return style.display !== 'none' && "
                        f"         style.visibility !== 'hidden' && "
                        f"         el.offsetParent !== null;"
                        f"}})()"
                    )
                    if visible:
                        return True
                except (ConnectionError, TimeoutError, BrowserError):
                    pass  # Transient error, retry
                time.sleep(0.2)
            return False
        finally:
            self._record_depth.reset(token)

    def wait_for_selector_hidden(
        self,
        selector: str,
        timeout: float = 30.0,
    ) -> bool:
        """
        Wait for element to be hidden or removed from DOM.

        Args:
            selector: CSS selector
            timeout: Maximum seconds to wait

        Returns:
            True if element became hidden, False if timeout
        """
        self._record_action(
            "wait_for_selector_hidden", selector=selector, timeout=timeout
        )
        token = self._record_depth.set(self._record_depth.get() + 1)
        try:
            escaped = escape_js_string(selector)
            start = time.time()
            while time.time() - start <= timeout:
                try:
                    hidden = self.evaluate(
                        f"(function() {{"
                        f"  const el = document.querySelector('{escaped}');"
                        f"  if (!el) return true;"  # Not in DOM = hidden
                        f"  const style = window.getComputedStyle(el);"
                        f"  return style.display === 'none' || "
                        f"         style.visibility === 'hidden' || "
                        f"         el.offsetParent === null;"
                        f"}})()"
                    )
                    if hidden:
                        return True
                except (ConnectionError, TimeoutError, BrowserError):
                    pass  # Transient error, retry
                time.sleep(0.2)
            return False
        finally:
            self._record_depth.reset(token)

    def wait_for_function(
        self,
        js_function: str,
        timeout: float = 30.0,
        polling_interval: float = 0.2,
    ) -> bool:
        """
        Wait for custom JavaScript function to return truthy value.

        Args:
            js_function: JavaScript expression that returns truthy/falsy
            timeout: Maximum seconds to wait
            polling_interval: Seconds between checks

        Returns:
            True if function returned truthy, False if timeout

        Example:
            browser.wait_for_function("document.querySelectorAll('.item').length > 5")
        """
        self._record_action(
            "wait_for_function",
            js_function=js_function,
            timeout=timeout,
            polling_interval=polling_interval,
        )
        token = self._record_depth.set(self._record_depth.get() + 1)
        try:
            start = time.time()
            while time.time() - start <= timeout:
                try:
                    result = self.evaluate(js_function)
                    if result:
                        return True
                except (ConnectionError, TimeoutError, BrowserError):
                    pass  # Transient error, retry
                time.sleep(polling_interval)
            return False
        finally:
            self._record_depth.reset(token)

    def wait_for_navigation(
        self,
        tab: Tab | str | None = None,
        timeout: float = 30.0,
        wait_until: str = "load",
    ) -> bool:
        """
        Wait for page navigation to complete.

        This is a convenience method that waits for page load state.
        Args:
            tab: Tab to wait for (defaults to current, accepts Tab, tab ID, or None)
            timeout: Maximum seconds to wait
            wait_until: "load" (default) or "domcontentloaded"

        Returns:
            True if navigation completed, False if timeout
        """
        resolved_tab = self._resolve_tab(tab)
        return self.wait_for_load_state(
            state=wait_until, tab=resolved_tab, timeout=timeout
        )

    # ─────────────────────────────────────────────────────────────────────────────
    # Accessibility Tree
    # ─────────────────────────────────────────────────────────────────────────────

    def accessibility_tree(
        self,
        tab: Tab | None = None,
        timeout: float | None = None,
        refresh: bool = False,
        cache: bool | None = None,
    ) -> AXNode:
        """
        Get accessibility tree like agent-browser snapshot.

        Args:
            tab: Tab to query (defaults to current)
            timeout: Operation timeout
            refresh: Force refresh even if cached
            cache: Cache result if caching enabled (default: follows session setting)

        Returns:
            AXNode tree with refs for targeting elements

        Note: Use Browser(cache_accessibility=True) to enable caching
              globally, or pass cache=True for per-call caching.
        """
        # Resolve tab
        target_tab = tab or self.current_tab
        if not target_tab:
            tabs = self.list_tabs()
            if not tabs:
                raise TabError("No tabs available")
            target_tab = tabs[0]
            self.current_tab = target_tab

        tab_id = target_tab.id

        # Check cache
        use_cache = cache if cache is not None else self.cache_accessibility
        if use_cache and not refresh and tab_id in self._accessibility_cache:
            return self._accessibility_cache[tab_id]

        async def _get_tree() -> AXNode:
            conn = await self._get_connection(target_tab)
            result = await self._send_cdp(
                conn,
                "Accessibility.getFullAXTree",
                domains=["Accessibility"],
                timeout=timeout,
            )
            nodes = result.get("nodes", [])
            return self._parse_ax_nodes(nodes)

        tree = self._run_async(_get_tree())

        if use_cache:
            self._accessibility_cache[tab_id] = tree

        return tree

    def _parse_ax_nodes(self, nodes: list[dict]) -> AXNode:
        """Parse CDP accessibility nodes into tree."""
        node_map: dict[str, AXNode] = {}

        # 1. First pass: Create all nodes in a flat map
        for node in nodes:
            node_id = node.get("nodeId", "")
            if not node_id:
                continue

            # Extract name
            name_obj = node.get("name", {})
            if isinstance(name_obj, dict):
                name = name_obj.get("value", "")
            else:
                name = str(name_obj) if name_obj else ""

            # Extract role
            role_obj = node.get("role", {})
            if isinstance(role_obj, dict):
                role = role_obj.get("value", "unknown")
            else:
                role = str(role_obj) if role_obj else "unknown"

            # Extract URL for links
            url = None
            for prop in node.get("properties", []):
                if prop.get("name") == "url":
                    url_val = prop.get("value", {})
                    if isinstance(url_val, dict):
                        url = url_val.get("value", "")
                    else:
                        url = str(url_val)
                    break

            # Extract level for headings
            level = None
            for prop in node.get("properties", []):
                if prop.get("name") == "level":
                    level_val = prop.get("value", {})
                    if isinstance(level_val, dict):
                        level = level_val.get("value")
                    break

            # Extract value for inputs
            value = None
            val_obj = node.get("value")
            if isinstance(val_obj, dict):
                value = val_obj.get("value")

            node_map[node_id] = AXNode(
                ref=node_id,
                role=role,
                name=name,
                value=value,
                url=url,
                level=level,
            )

        # 2. Second pass: Build tree structure
        child_refs = set()
        for node in nodes:
            parent_id = node.get("nodeId")
            if not parent_id:
                continue
            parent_ax = node_map.get(parent_id)
            if not parent_ax:
                continue

            # Link via childIds (Standard for getFullAXTree)
            for child_id in node.get("childIds", []):
                child_ax = node_map.get(child_id)
                if child_ax and child_ax not in parent_ax.children:
                    parent_ax.children.append(child_ax)
                    child_ax.parent = parent_ax
                    child_refs.add(child_id)

            # Link via parentId (Backup for some CDP modes)
            parent_id_attr = node.get("parentId")
            if parent_id_attr:
                actual_parent = node_map.get(parent_id_attr)
                if actual_parent and parent_ax not in actual_parent.children:
                    actual_parent.children.append(parent_ax)
                    parent_ax.parent = actual_parent
                    child_refs.add(parent_id)

        # 3. Identify Root: Preferred node with no parentId or first node that isn't a child
        root_nodes: list[AXNode] = []
        for n in nodes:
            node_id = n.get("nodeId")
            if node_id and node_id not in child_refs:
                ax_node = node_map.get(node_id)
                if ax_node:
                    root_nodes.append(ax_node)

        if root_nodes:
            # Generally the first node that isn't a child is our root
            return root_nodes[0]

        return AXNode(ref="root", role="document", name="Empty Tree")

    def snapshot(self, tab: Tab | None = None) -> str:
        """Get snapshot string (alias for accessibility_tree().to_tree_str())."""
        tree = self.accessibility_tree(tab)
        return tree.to_tree_str()

    def find_by_ref(self, ref: str, tab: Tab | None = None) -> AXNode | None:
        """
        Find a single node by its ref.

        Args:
            ref: Node ref to find
            tab: Optional tab to query

        Returns:
            AXNode if found, None otherwise
        """
        tree = self.accessibility_tree(tab)
        for node in [tree] + self._flatten_tree(tree):
            if node.ref == ref or node.ref == ref.lstrip("axnode@"):
                return node
        return None

    def _flatten_tree(self, node: AXNode) -> list[AXNode]:
        """Recursively flatten an AXNode tree into a list."""
        result = []
        for child in node.children:
            result.append(child)
            result.extend(self._flatten_tree(child))
        return result

    def find_by_name(
        self,
        name: str,
        tab: Tab | None = None,
        *,
        exact: bool = False,
        interactive_only: bool = False,
    ) -> list[AXNode]:
        """
        Find nodes by accessible name.

        Args:
            name: Text to search for
            tab: Optional tab to query
            exact: If True, match name exactly
            interactive_only: If True, only return interactive elements

        Returns:
            List of matching AXNode instances
        """
        tree = self.accessibility_tree(tab=tab)
        return tree.find_by_name(name, exact=exact, interactive_only=interactive_only)

    def find_by_value(self, value: str, tab: Tab | None = None) -> list[AXNode]:
        """
        Find nodes by value content.

        Args:
            value: Value substring to match
            tab: Optional tab to query

        Returns:
            List of matching AXNode instances
        """
        tree = self.accessibility_tree(tab=tab)
        results = []
        def search(node):
            if node.value and value in str(node.value):
                results.append(node)
            for child in node.children:
                search(child)
        search(tree)
        return results

    def get_links(self, tab: Tab | None = None) -> list[dict]:
        """
        Extract all links from page.

        Returns:
            List of dicts with keys: text, ref, url
        """
        tree = self.accessibility_tree(tab)
        links = []
        for node in tree.find_by_role("link"):
            links.append({
                "text": node.name,
                "ref": node.ref,
                "url": node.url,
            })
        return links

    def get_text(self, ref: str | None = None, tab: Tab | None = None) -> str:
        """
        Extract text content.

        Args:
            ref: Optional node ref to extract text from
            tab: Optional tab to query

        Returns:
            Text content (empty string if ref not found)
        """
        tree = self.accessibility_tree(tab)
        if ref:
            node = tree.find(ref)
            if node:
                return node.name or ""
            return ""
        return tree.name or ""

    def find_links(
        self,
        text_contains: str | None = None,
        tab: Tab | None = None,
    ) -> list[dict]:
        """
        Find links matching text pattern.

        Args:
            text_contains: Filter links by text (case-insensitive substring match)
            tab: Optional tab to query

        Returns:
            List of link dicts matching the filter
        """
        links = self.get_links(tab)
        if text_contains:
            links = [
                link for link in links
                if text_contains.lower() in link["text"].lower()
            ]
        return links

    # ─────────────────────────────────────────────────────────────────────────────
    # Interactions
    # ─────────────────────────────────────────────────────────────────────────────

    def click_by_text(
        self,
        text: str,
        tab: Tab | None = None,
        timeout: float | None = None,
        *,
        double: bool = False,
        button: str = "left",
    ) -> bool:
        """
        Click element containing text (links, buttons, etc).

        **Warning:** If multiple elements match the text, this method will only click
        the first one encountered in the DOM. For disambiguation, it is recommended
        to use `accessibility_tree()` to find the desired node and use its `ref` with
        the `click()` method.

        Args:
            text: Text to search for
            tab: Tab to operate on (defaults to current)
            timeout: Operation timeout
            double: If True, perform double-click
            button: Mouse button - "left", "right", or "middle"

        Returns:
            True if clicked, False if not found
        """
        self._record_action(
            "click_by_text", text=text, timeout=timeout, double=double, button=button
        )
        token = self._record_depth.set(self._record_depth.get() + 1)

        async def _click_by_text_async(target_tab: Tab | None = None) -> bool:
            try:
                conn = await self._get_connection(target_tab)
                escaped_text = escape_js_string(text)
                js_code = (
                    _CLICK_BY_TEXT_JS.replace("{text}", escaped_text)
                    .replace("{double}", str(double))
                    .replace("{button}", button)
                )
                result = await self._send_cdp(
                    conn,
                    "Runtime.evaluate",
                    {"expression": js_code, "returnByValue": True},
                    domains=["Runtime"],
                    timeout=timeout,
                )
                # Result structure: {"result": {"type": "boolean", "value": true}}
                return result.get("result", {}).get("value", False) is True
            finally:
                pass

        try:
            return self._run_async(_click_by_text_async(tab))
        finally:
            self._record_depth.reset(token)

    def click(
        self,
        ref: str,
        tab: Tab | None = None,
        timeout: float | None = None,
        *,
        double: bool = False,
        button: str = "left",
    ) -> bool:
        """
        Click element by accessibility ref.

        Args:
            ref: Accessibility node ID
            tab: Tab to operate on (defaults to current)
            timeout: Operation timeout
            double: If True, perform double-click
            button: Mouse button - "left", "right", or "middle"

        Returns:
            True if clicked, False if not found
        """
        _validate_ref(ref)
        self._record_action(
            "click", ref=ref, timeout=timeout, double=double, button=button
        )
        token = self._record_depth.set(self._record_depth.get() + 1)

        async def _click_async(target_tab: Tab | None = None) -> bool:
            try:
                conn = await self._get_connection(target_tab)
                # ... same as original ...
                # Get accessibility tree nodes to find backend info and name
                tree_result = await self._send_cdp(
                    conn,
                    "Accessibility.getFullAXTree",
                    domains=["Accessibility"],
                    timeout=timeout,
                )
                nodes = tree_result.get("nodes", [])

                # Find matching node and its name
                backend_node_id = None
                node_name = None
                for node in nodes:
                    if node.get("nodeId") == ref:
                        backend_node_id = node.get("backendDOMNodeId")
                        # Extract name
                        name_obj = node.get("name", {})
                        if isinstance(name_obj, dict):
                            node_name = name_obj.get("value", "")
                        else:
                            node_name = str(name_obj) if name_obj else ""
                        break

                if backend_node_id:
                    # Try direct targeted click first
                    try:
                        resolve_res = await self._send_cdp(
                            conn,
                            "DOM.resolveNode",
                            {"backendNodeId": backend_node_id},
                            domains=["DOM"],
                            timeout=timeout,
                        )
                        remote_obj = resolve_res.get("object")

                        if remote_obj and remote_obj.get("objectId"):
                            # Get box model for coordinates
                            box_res = await self._send_cdp(
                                conn,
                                "DOM.getBoxModel",
                                {"objectId": remote_obj["objectId"]},
                                domains=["DOM"],
                                timeout=timeout,
                            )
                            content = box_res.get("model", {}).get("content")

                            if content and len(content) >= 8:
                                # Calculate center of the node
                                x = (
                                    content[0] + content[2] + content[4] + content[6]
                                ) / 4
                                y = (
                                    content[1] + content[3] + content[5] + content[7]
                                ) / 4

                                # Perform native-like click via Input
                                # A double click requires two sets of press/release
                                # with clickCount=2, but usually one clickCount=1
                                # followed by one clickCount=2 sequence works best.
                                click_count = 2 if double else 1

                                await self._send_cdp(
                                    conn,
                                    "Input.dispatchMouseEvent",
                                    {
                                        "type": "mousePressed",
                                        "x": x,
                                        "y": y,
                                        "button": button,
                                        "clickCount": click_count,
                                    },
                                    domains=["Input"],
                                )
                                await self._send_cdp(
                                    conn,
                                    "Input.dispatchMouseEvent",
                                    {
                                        "type": "mouseReleased",
                                        "x": x,
                                        "y": y,
                                        "button": button,
                                        "clickCount": click_count,
                                    },
                                    domains=["Input"],
                                )
                                return True
                            else:
                                # Fallback to JS if coordinates unavailable
                                click_fn: str
                                if double:
                                    click_fn = (
                                        "this.dispatchEvent(new MouseEvent("
                                        "'dblclick', {bubbles: true}))"
                                    )
                                elif button == "right":
                                    click_fn = (
                                        "this.dispatchEvent(new MouseEvent("
                                        "'contextmenu', {bubbles: true}))"
                                    )
                                else:
                                    click_fn = "this.click()"

                                await self._send_cdp(
                                    conn,
                                    "Runtime.callFunctionOn",
                                    {
                                        "functionDeclaration": (
                                            "function() {"
                                            "  this.scrollIntoView("
                                            "    {block: 'center', inline: 'center'}"
                                            "  );"
                                            f"  {click_fn};"
                                            "}"
                                        ),
                                        "objectId": remote_obj["objectId"],
                                    },
                                    domains=["Runtime"],
                                    timeout=timeout,
                                )
                                return True
                    except Exception:
                        # Fall through to text-based click if targeted click fails
                        pass

                # Fallback: click by text if we found a name for the node
                if node_name:
                    # Call click_by_text and await if it returns a Task
                    result = self.click_by_text(
                        node_name, tab=target_tab, timeout=timeout
                    )
                    if asyncio.iscoroutine(result) or asyncio.isfuture(result):
                        return await result
                    return result

                return False
            finally:
                pass

        try:
            return self._run_async(_click_async(tab))
        finally:
            self._record_depth.reset(token)

    def type_text(
        self,
        ref: str,
        text: str,
        tab: Tab | None = None,
        timeout: float | None = None,
    ) -> bool:
        """
        Type text into element by accessibility ref.

        Args:
            ref: Accessibility node ID (from tree)
            text: Text to type
            tab: Tab to operate on (defaults to current)
            timeout: Operation timeout

        Returns:
            True if typed, False if not found
        """
        _validate_ref(ref)
        self._record_action("type_text", ref=ref, text=text, timeout=timeout)
        token = self._record_depth.set(self._record_depth.get() + 1)

        async def _type_async(target_tab: Tab | None = None) -> bool:
            conn = await self._get_connection(target_tab)

            # Get tree nodes once to find backend info and name
            tree_result = await self._send_cdp(
                conn,
                "Accessibility.getFullAXTree",
                domains=["Accessibility"],
                timeout=timeout,
            )
            nodes = tree_result.get("nodes", [])

            backend_node_id = None
            node_name = None
            for node in nodes:
                if node.get("nodeId") == ref:
                    backend_node_id = node.get("backendDOMNodeId")
                    # Extract name
                    name_obj = node.get("name", {})
                    if isinstance(name_obj, dict):
                        node_name = name_obj.get("value", "")
                    else:
                        node_name = str(name_obj) if name_obj else ""
                    break

            if backend_node_id:
                # Try direct targeted typing
                try:
                    resolve_res = await self._send_cdp(
                        conn,
                        "DOM.resolveNode",
                        {"backendNodeId": backend_node_id},
                        domains=["DOM"],
                        timeout=timeout,
                    )
                    # CDP returns {"object": RemoteObject} with objectId
                    remote_obj = resolve_res.get("object")

                    if remote_obj and remote_obj.get("objectId"):
                        # Type via JavaScript on the resolved element
                        # Note: callFunctionOn binds the object to `this`, not an argument
                        escaped_text = escape_js_string(text)
                        await self._send_cdp(
                            conn,
                            "Runtime.callFunctionOn",
                            {
                                "functionDeclaration": (
                                    f"function() {{"
                                    "  this.scrollIntoView("
                                    "    {block: 'center', inline: 'center'}"
                                    "  );"
                                    f"  this.focus();"
                                    f"  this.value = '{escaped_text}';"
                                    "  this.dispatchEvent("
                                    "    new Event('input', {bubbles: true})"
                                    "  );"
                                    "  this.dispatchEvent("
                                    "    new Event('change', {bubbles: true})"
                                    "  );"
                                    f"}}"
                                ),
                                "objectId": remote_obj["objectId"],
                            },
                            domains=["Runtime"],
                            timeout=timeout,
                        )
                        return True
                except Exception:
                    # Fall through to name-based typing if targeted typing fails
                    pass

            # Fallback: type by name/placeholder/id if we found a name
            if node_name:
                # Call type_by_name and await if it returns a Task
                result = self.type_by_name(
                    node_name, text, tab=target_tab, timeout=timeout
                )
                if asyncio.iscoroutine(result) or asyncio.isfuture(result):
                    return await result
                return result

            return False

        try:
            return self._run_async(_type_async(tab))
        finally:
            self._record_depth.reset(token)

    def _find_form_element(
        self,
        identifier: str,
        tab: Tab | None = None,
        timeout: float | None = None,
    ) -> str | None:
        """
        Find a form element's accessibility ref by name, label, etc.

        Args:
            identifier: Name, ID, label text, or placeholder
            tab: Tab to operate on
            timeout: Operation timeout

        Returns:
            Accessibility ref (axnode@ID) or None if not found
        """

        async def _find():
            conn = await self._get_connection(tab)
            escaped_id = escape_js_string(identifier)
            js_code = _FIND_FORM_ELEMENT_JS.replace("{identifier}", escaped_id)

            # Find element and return it as an object
            res = await self._send_cdp(
                conn,
                "Runtime.evaluate",
                {"expression": js_code, "returnByValue": False},
                domains=["Runtime"],
                timeout=timeout,
            )

            result_obj = res.get("result", {})
            if result_obj.get("type") == "object" and result_obj.get("objectId"):
                object_id = result_obj["objectId"]

                # Get backendNodeId
                # 1. Map object to nodeId
                node_res = await self._send_cdp(
                    conn,
                    "DOM.requestNode",
                    {"objectId": object_id},
                    domains=["DOM"],
                    timeout=timeout,
                )
                node_id = node_res.get("nodeId")

                if node_id:
                    # 2. Get backendNodeId from nodeId
                    desc_res = await self._send_cdp(
                        conn,
                        "DOM.describeNode",
                        {"nodeId": node_id},
                        domains=["DOM"],
                        timeout=timeout,
                    )
                    backend_node_id = desc_res.get("node", {}).get("backendNodeId")

                    if backend_node_id:
                        # 3. Find AX node with this backendDOMNodeId
                        tree_res = await self._send_cdp(
                            conn,
                            "Accessibility.getFullAXTree",
                            domains=["Accessibility"],
                            timeout=timeout,
                        )
                        for node in tree_res.get("nodes", []):
                            if node.get("backendDOMNodeId") == backend_node_id:
                                return node.get("nodeId")
            return None

        return self._run_async(_find())

    def type_by_name(
        self,
        name: str,
        text: str,
        tab: Tab | None = None,
        timeout: float | None = None,
    ) -> bool:
        """
        Type text into an input field found by its name, placeholder, or ID.

        Args:
            name: The name attribute, placeholder, label, or ID of the field
            text: Text to type
            tab: Tab to operate on
            timeout: Operation timeout

        Returns:
            True if typed, False if not found
        """
        self._record_action("type_by_name", name=name, text=text, timeout=timeout)
        token = self._record_depth.set(self._record_depth.get() + 1)
        try:
            ref = self._find_form_element(name, tab=tab, timeout=timeout)
            if ref:
                return self.type_text(ref, text, tab=tab, timeout=timeout)
            return False
        finally:
            self._record_depth.reset(token)

    def hover(
        self, ref: str, tab: Tab | None = None, timeout: float | None = None
    ) -> bool:
        """
        Hover over element by accessibility ref.

        Args:
            ref: Accessibility node ID
            tab: Tab to operate on (defaults to current)
            timeout: Operation timeout

        Returns:
            True if hovered, False if not found
        """
        _validate_ref(ref)

        self._record_action("hover", ref=ref, timeout=timeout)
        token = self._record_depth.set(self._record_depth.get() + 1)

        async def _hover_async(target_tab: Tab | None = None) -> bool:
            try:
                conn = await self._get_connection(target_tab)

                # Get accessibility tree to find backend node ID
                tree_result = await self._send_cdp(
                    conn,
                    "Accessibility.getFullAXTree",
                    domains=["Accessibility"],
                    timeout=timeout,
                )
                nodes = tree_result.get("nodes", [])

                backend_node_id = None
                for node in nodes:
                    if node.get("nodeId") == ref:
                        backend_node_id = node.get("backendDOMNodeId")
                        break

                if backend_node_id:
                    try:
                        resolve_res = await self._send_cdp(
                            conn,
                            "DOM.resolveNode",
                            {"backendNodeId": backend_node_id},
                            domains=["DOM"],
                            timeout=timeout,
                        )
                        remote_obj = resolve_res.get("object")

                        if remote_obj and remote_obj.get("objectId"):
                            # Hover via JavaScript on the resolved element
                            # Note: callFunctionOn binds the object to `this`, not an argument
                            await self._send_cdp(
                                conn,
                                "Runtime.callFunctionOn",
                                {
                                    "functionDeclaration": (
                                        "function() {"
                                        "  this.scrollIntoView("
                                        "    {block: 'center', inline: 'center'}"
                                        "  );"
                                        "  var ev = new MouseEvent("
                                        "    'mouseenter', {bubbles: true}"
                                        "  );"
                                        "  this.dispatchEvent(ev);"
                                        "  ev = new MouseEvent("
                                        "    'mouseover', {bubbles: true}"
                                        "  );"
                                        "  this.dispatchEvent(ev);"
                                        "}"
                                    ),
                                    "objectId": remote_obj["objectId"],
                                },
                                domains=["Runtime"],
                                timeout=timeout,
                            )
                            return True
                    except Exception:
                        pass

                return False
            finally:
                pass

        try:
            return self._run_async(_hover_async(tab))
        finally:
            self._record_depth.reset(token)

    def press_key(
        self,
        key: str,
        *,
        modifiers: list[str] | None = None,
        tab: Tab | None = None,
        timeout: float | None = None,
    ) -> None:
        """
        Press a key (optionally with modifiers).

        Uses CDP Input.dispatchKeyEvent for realistic keyboard input.

        Args:
            key: Key to press (e.g., "a", "Enter", "Tab", "Escape")
            modifiers: List of modifiers - "Control", "Shift", "Alt", "Meta"
            tab: Tab to operate on (defaults to current)
            timeout: Operation timeout

        Example:
            browser.press_key("c", modifiers=["Control"])  # Ctrl+C
            browser.press_key("Enter")
            browser.press_key("Tab")
        """
        modifier_flags = 0
        if modifiers:
            mod_map = {"Alt": 1, "Control": 2, "Meta": 4, "Shift": 8}
            for mod in modifiers:
                modifier_flags |= mod_map.get(mod.capitalize(), 0)

        async_key = _key_to_key_definition(key, modifier_flags)
        self._record_action("press_key", key=key, modifiers=modifiers, timeout=timeout)
        token = self._record_depth.set(self._record_depth.get() + 1)

        async def _press_async(target_tab: Tab | None = None) -> None:
            try:
                conn = await self._get_connection(target_tab)

                # Enable Input domain (may not be supported on all targets)
                try:
                    await self._send_cdp(conn, "Input.enable", timeout=timeout)
                except CDPError:
                    # Input.enable not supported, continue anyway
                    pass

                # Key down
                await self._send_cdp(
                    conn,
                    "Input.dispatchKeyEvent",
                    {**async_key, "type": "keyDown"},
                    timeout=timeout,
                )

                # Key up
                await self._send_cdp(
                    conn,
                    "Input.dispatchKeyEvent",
                    {**async_key, "type": "keyUp"},
                    timeout=timeout,
                )
            finally:
                pass

        try:
            self._run_async(_press_async(tab))
        finally:
            self._record_depth.reset(token)

    def type_slowly(
        self,
        ref: str,
        text: str,
        delay: float = 0.05,
        tab: Tab | None = None,
        timeout: float | None = None,
    ) -> bool:
        """
        Type text character by character (simulates human typing).

        Uses CDP Input.insertText for each character, with configurable delay.
        More realistic than type_text() which sets the value directly.

        Args:
            ref: Accessibility node ID
            text: Text to type
            delay: Delay between characters in seconds (default: 0.05 = 50ms)
            tab: Tab to operate on (defaults to current)
            timeout: Operation timeout

        Returns:
            True if all characters typed, False if element not found
        """
        _validate_ref(ref)
        self._record_action(
            "type_slowly", ref=ref, text=text, delay=delay, timeout=timeout
        )
        token = self._record_depth.set(self._record_depth.get() + 1)

        async def _type_slowly_async(target_tab: Tab | None = None) -> bool:
            try:
                conn = await self._get_connection(target_tab)
                # ... same as original ...
                # Focus on the element first
                tree_result = await self._send_cdp(
                    conn,
                    "Accessibility.getFullAXTree",
                    domains=["Accessibility"],
                    timeout=timeout,
                )
                nodes = tree_result.get("nodes", [])

                backend_node_id = None
                for node in nodes:
                    if node.get("nodeId") == ref:
                        backend_node_id = node.get("backendDOMNodeId")
                        break

                if not backend_node_id:
                    return False

                try:
                    resolve_res = await self._send_cdp(
                        conn,
                        "DOM.resolveNode",
                        {"backendNodeId": backend_node_id},
                        domains=["DOM"],
                        timeout=timeout,
                    )
                    remote_obj = resolve_res.get("object")

                    if remote_obj and remote_obj.get("objectId"):
                        # Focus the element
                        await self._send_cdp(
                            conn,
                            "Runtime.callFunctionOn",
                            {
                                "functionDeclaration": "(function(el) { el.focus(); })",
                                "objectId": remote_obj["objectId"],
                            },
                            domains=["Runtime"],
                            timeout=timeout,
                        )
                except Exception:
                    pass

                # Enable Input domain (may not be supported on all targets)
                try:
                    await self._send_cdp(conn, "Input.enable", timeout=timeout)
                except CDPError:
                    # Input.enable not supported, continue anyway
                    pass

                # Type each character
                for char in text:
                    await self._send_cdp(
                        conn,
                        "Input.insertText",
                        {"text": char},
                        timeout=timeout,
                    )
                    if delay > 0:
                        await asyncio.sleep(delay)

                return True
            finally:
                pass

        try:
            return self._run_async(_type_slowly_async(tab))
        finally:
            self._record_depth.reset(token)

    def fill_form(
        self,
        fields: dict[str, str],
        tab: Tab | None = None,
        timeout: float | None = None,
        raise_on_error: bool = False,
    ) -> dict[str, bool]:
        """
        Fill multiple form fields.

        Args:
            fields: Dict of {label_or_name: value}
            tab: Tab to operate on (defaults to current)
            timeout: Operation timeout
            raise_on_error: If True, raises BrowserError if any field fails

        Returns:
            Dict mapping each field to a success boolean
        """

        self._record_action(
            "fill_form", fields=fields, timeout=timeout, raise_on_error=raise_on_error
        )
        token = self._record_depth.set(self._record_depth.get() + 1)

        async def _fill() -> dict[str, bool]:
            try:
                conn = await self._get_connection(tab)
                await self._send_cdp(
                    conn, "Runtime.enable", timeout=timeout or self.timeout
                )

                results = {}
                for label_or_name, value in fields.items():
                    escaped_value = escape_js_string(value)
                    escaped_label = escape_js_string(label_or_name)
                    js_code = _FILL_FORM_JS.replace("{label}", escaped_label).replace(
                        "{value}", escaped_value
                    )
                    res = await self._send_cdp(
                        conn,
                        "Runtime.evaluate",
                        {"expression": js_code, "returnByValue": True},
                        timeout=timeout,
                    )
                    # Runtime.evaluate returns {"result": {"type": "boolean", "value": ...}}
                    result_data = res.get("result", {})
                    success = (
                        result_data.get("value")
                        if isinstance(result_data, dict)
                        else False
                    )
                    results[label_or_name] = bool(success)

                # Track failures with reasons
                if not all(results.values()):
                    failed = {k: v for k, v in results.items() if not v}
                    logger.warning(f"fill_form failed for fields: {failed}")
                    if raise_on_error:
                        raise BrowserError(
                            f"fill_form failed for fields: {list(failed.keys())}",
                            context={"failed_fields": failed},
                        )
                return results
            finally:
                pass

        try:
            return self._run_async(_fill())
        finally:
            self._record_depth.reset(token)

    # ─────────────────────────────────────────────────────────────────────────────
    # Device Emulation
    # ─────────────────────────────────────────────────────────────────────────────

    def emulate_device(
        self, device: str | dict | None = None, tab: Tab | None = None
    ) -> None:
        """
        Emulate a mobile device or disable emulation.

        Overrides user agent, viewport, and touch events to simulate
        mobile devices.

        Args:
            device: Device name (e.g., "iPhone 14", "iPad Pro") or custom dict
                   with userAgent, viewport, touch, mobile properties.
                   Pass None to disable emulation.

            tab: Tab to emulate on (defaults to current)

        Example:
            # Use built-in device
            browser.emulate_device("iPhone 14")
            browser.emulate_device("iPad Pro")
            browser.emulate_device("Samsung Galaxy S21")

            # Custom device
            browser.emulate_device({
                "userAgent": "Custom User Agent",
                "viewport": {"width": 375, "height": 667},
                "touch": True,
                "mobile": True,
            })

            # Disable emulation
            browser.emulate_device(None)

        Available Devices:
            - iPhone 14 Pro
            - iPhone 14
            - iPhone SE
            - iPad Pro 12.9
            - iPad Air
            - Samsung Galaxy S21
            - Samsung Galaxy S20
            - Google Pixel 7
            - Google Pixel 6
            - Motorola Moto G4
        """
        async def _emulate() -> None:
            conn = await self._get_connection(tab)

            # Enable Emulation domain first
            try:
                await self._send_cdp(
                    conn, "Emulation.enable", domains=["Emulation"]
                )
            except:
                # Emulation domain not available, skip emulation
                return

            if device is None:
                # Disable emulation
                try:
                    await self._send_cdp(
                        conn, "Emulation.clearDeviceMetricsOverride", domains=["Emulation"]
                    )
                except:
                    pass  # Ignore if not available
                
                await self._send_cdp(
                    conn,
                    "Emulation.setUserAgentOverride",
                    {"userAgent": ""},
                    domains=["Emulation"],
                )
                return

            # Get device descriptor
            if isinstance(device, str):
                if device not in _DEVICES:
                    raise ValueError(
                        f"Unknown device: {device}. Available: {list(_DEVICES.keys())}"
                    )
                device_config = _DEVICES[device]
            else:
                device_config = device

            # Set user agent
            await self._send_cdp(
                conn,
                "Emulation.setUserAgentOverride",
                {"userAgent": device_config["userAgent"]},
                domains=["Emulation"],
            )

            # Set viewport
            viewport = device_config.get("viewport", {})
            await self._send_cdp(
                conn,
                "Emulation.setViewport",
                {
                    "width": viewport.get("width", 800),
                    "height": viewport.get("height", 600),
                    "deviceScaleFactor": viewport.get("deviceScaleFactor", 1),
                    "scale": viewport.get("scale", 1),
                    "mobile": device_config.get("mobile", False),
                },
                domains=["Emulation"],
            )

            # Enable touch
            if device_config.get("touch", False):
                try:
                    await self._send_cdp(
                        conn,
                        "Emulation.setTouchEmulationEnabled",
                        {"enabled": True},
                        domains=["Emulation"],
                    )
                except:
                    pass  # Ignore if not available

        self._run_async(_emulate())

    def get_emulated_device(self, tab: Tab | None = None) -> dict | None:
        """
        Get the currently emulated device configuration.

        Returns:
            Device config dict or None if not emulating

        Example:
            device = browser.get_emulated_device()
            if device:
                print(f"Emulating: {device}")
        """
        async def _get() -> dict | None:
            conn = await self._get_connection(tab)
            # Get current metrics
            try:
                result = await self._send_cdp(
                    conn, "Emulation.getDeviceMetricsOverride", domains=["Emulation"]
                )
            except Exception:
                return None
            metrics = result.get("metrics", {})
            if not metrics:
                return None

            # Get user agent
            ua_result = await self._send_cdp(
                conn, "Emulation.getUserAgentOverride", domains=["Emulation"]
            )
            ua = ua_result.get("userAgent", "")

            return {
                "userAgent": ua,
                "viewport": {
                    "width": metrics.get("width", 0),
                    "height": metrics.get("height", 0),
                    "deviceScaleFactor": metrics.get("deviceScaleFactor", 1),
                },
                "touch": metrics.get("touchOverride", False),
                "mobile": metrics.get("isMobile", False),
            }

        return self._run_async(_get())

    # ─────────────────────────────────────────────────────────────────────────────
    # Screenshots & Content
    # ─────────────────────────────────────────────────────────────────────────────

    def screenshot(
        self, path: str, tab: Tab | None = None, timeout: float | None = None
    ) -> str:
        """
        Take screenshot and save to path.

        Args:
            path: File path to save PNG
            tab: Tab to screenshot (defaults to current)
            timeout: Operation timeout

        Returns:
            Path to saved file

        Raises:
            BrowserError: If screenshot fails
        """

        async def _screenshot() -> str:
            conn = await self._get_connection(tab)
            result = await self._send_cdp(
                conn,
                "Page.captureScreenshot",
                {"format": "png"},
                domains=["Page"],
                timeout=timeout,
            )

            data = result.get("data")
            if data:
                with open(path, "wb") as f:
                    f.write(base64.b64decode(data))
                return path
            raise BrowserError("No screenshot data returned")

        return self._run_async(_screenshot())

    # ─────────────────────────────────────────────────────────────────────────────
    # Visual Regression & Comparison
    # ─────────────────────────────────────────────────────────────────────────────

    def _import_image_deps(self) -> tuple[Any, Any]:
        """Lazy import optional dependencies for image comparison."""
        try:
            import numpy as np  # type: ignore
            from PIL import Image  # type: ignore

            return np, Image
        except ImportError:
            raise ImportError(
                "Image comparison requires Pillow and numpy. "
                "Install them with: pip install browser-hybrid[compare]"
            )

    def compare_screenshots(
        self,
        baseline: str,
        current: str,
        threshold: float = 0.0,
        output_diff: str | None = None,
        region: tuple[int, int, int, int] | None = None,
    ) -> ComparisonResult:
        """
        Compare two screenshots pixel-by-pixel.

        Args:
            baseline: Path to baseline screenshot
            current: Path to current screenshot
            threshold: Allowed difference percentage (0.0 to 100.0)
            output_diff: Optional path to save diff image
            region: Optional crop region (x, y, width, height)

        Returns:
            ComparisonResult
        """
        # Validate threshold
        if threshold < 0.0:
            raise ValueError(f"threshold must be >= 0.0, got {threshold}")
        if threshold > 100.0:
            raise ValueError(
                f"threshold must be <= 100.0 (percentage), got {threshold}"
            )

        if not os.path.exists(baseline):
            raise FileNotFoundError(f"Baseline screenshot not found: {baseline}")
        if not os.path.exists(current):
            raise FileNotFoundError(f"Current screenshot not found: {current}")

        np, Image = self._import_image_deps()  # noqa: N806

        # Baseline image
        with Image.open(baseline) as b:
            b_img = b.convert("RGB")
            if region:
                x, y, w, h = region
                b_img = b_img.crop((x, y, x + w, y + h))
            baseline_arr = np.array(b_img)
            baseline_size = b_img.size

        # Current image
        with Image.open(current) as c:
            c_img = c.convert("RGB")
            if region:
                x, y, w, h = region
                c_img = c_img.crop((x, y, x + w, y + h))
            current_arr = np.array(c_img)
            current_size = c_img.size

        # Dimension check
        if baseline_arr.shape != current_arr.shape:
            raise ValueError(
                f"Image dimensions differ: {baseline_arr.shape} vs {current_arr.shape}"
            )

        # Calculate pixel-by-pixel diff
        # np.abs for difference, then check if any channel > 0
        diff = np.abs(baseline_arr.astype(np.int16) - current_arr.astype(np.int16))
        diff_mask = np.any(diff > 0, axis=2)
        diff_pixels = int(np.sum(diff_mask))
        total_pixels = baseline_arr.shape[0] * baseline_arr.shape[1]
        diff_percentage = (
            (diff_pixels / total_pixels) * 100 if total_pixels > 0 else 0.0
        )

        match = diff_percentage <= threshold

        # Save diff image if requested
        if output_diff:
            # Highlight differences in red over the current image
            with Image.open(current) as d:
                diff_img = d.convert("RGB")
                if region:
                    x, y, w, h = region
                    diff_img = diff_img.crop((x, y, x + w, y + h))

                diff_arr = np.array(diff_img)
                diff_arr[diff_mask] = [255, 0, 0]  # Red for differences
                Image.fromarray(diff_arr).save(output_diff)

        message = f"Visual match: {match} ({diff_percentage:.2f}% different, {diff_pixels} pixels differ)"

        return ComparisonResult(
            match=match,
            diff_pixels=diff_pixels,
            diff_percentage=diff_percentage,
            baseline_size=baseline_size,
            current_size=current_size,
            diff_path=output_diff,
            message=message,
        )

    def screenshot_and_compare(
        self,
        path: str,
        baseline: str,
        threshold: float = 0.0,
        output_diff: str | None = None,
        region: tuple[int, int, int, int] | None = None,
    ) -> ComparisonResult:
        """
        Take screenshot and compare against baseline in one call.

        Args:
            path: Path to save current screenshot
            baseline: Path to baseline screenshot
            threshold: Allowed difference percentage
            output_diff: Optional path to save diff image
            region: Optional crop region

        Returns:
            ComparisonResult
        """
        self.screenshot(path)
        return self.compare_screenshots(
            baseline=baseline,
            current=path,
            threshold=threshold,
            output_diff=output_diff,
            region=region,
        )

    def assert_visual_match(
        self,
        baseline: str,
        threshold: float = 0.0,
        update_baseline: bool = False,
        region: tuple[int, int, int, int] | None = None,
    ) -> ComparisonResult:
        """
        Assert current page matches baseline screenshot.

        Args:
            baseline: Path to baseline screenshot
            threshold: Allowed difference percentage
            update_baseline: If True and mismatch, update baseline (default: False)
            region: Optional crop region

        Returns:
            ComparisonResult

        Raises:
            AssertionError: If images differ beyond threshold
        """
        import shutil
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            current_path = tmp.name

        np, Image = self._import_image_deps()  # noqa: N806

        try:
            self.screenshot(current_path)

            if not os.path.exists(baseline):
                if update_baseline:
                    shutil.copy(current_path, baseline)

                    with Image.open(baseline) as img:
                        size = img.size
                    return ComparisonResult(
                        match=True,
                        diff_pixels=0,
                        diff_percentage=0.0,
                        baseline_size=size,
                        current_size=size,
                        message="New baseline created.",
                    )
                raise FileNotFoundError(f"Baseline not found: {baseline}")

            result = self.compare_screenshots(
                baseline=baseline,
                current=current_path,
                threshold=threshold,
                region=region,
            )

            if not result.match:
                if update_baseline:
                    shutil.copy(current_path, baseline)
                    result.message += " (Baseline updated)"
                    return result

                # Check for diff_pixels correctly
                raise AssertionError(
                    f"Visual mismatch: {result.diff_percentage:.2f}% differs. "
                    f"Diff pixels: {result.diff_pixels}"
                )

            return result
        finally:
            if os.path.exists(current_path):
                os.remove(current_path)

    def pdf(
        self,
        path: str,
        tab: Tab | None = None,
        timeout: float | None = None,
        landscape: bool = False,
        paper_width: float = 8.5,
        paper_height: float = 11.0,
        margin_top: float = 0.4,
        margin_bottom: float = 0.4,
        margin_left: float = 0.4,
        margin_right: float = 0.4,
        print_background: bool = False,
        scale: float = 1.0,
        page_ranges: str | None = None,
        header_template: str | None = None,
        footer_template: str | None = None,
        prefer_css_page_size: bool = False,
    ) -> str:
        """
        Generate PDF from current page.

        Args:
            path: File path to save PDF
            tab: Tab to generate PDF from (defaults to current)
            timeout: Operation timeout
            landscape: Page orientation (default: portrait)
            paper_width: Paper width in inches (default: 8.5)
            paper_height: Paper height in inches (default: 11)
            margin_top: Top margin in inches (default: 0.4)
            margin_bottom: Bottom margin in inches (default: 0.4)
            margin_left: Left margin in inches (default: 0.4)
            margin_right: Right margin in inches (default: 0.4)
            print_background: Print background graphics (default: False)
            scale: Scale factor (default: 1.0)
            page_ranges: Paper ranges to print, e.g., "1-5, 9" (default: all)
            header_template: HTML template for page header
            footer_template: HTML template for page footer
            prefer_css_page_size: Use CSS @page size (default: False)

        Returns:
            Path to saved PDF file

        Raises:
            BrowserError: If PDF generation fails
        """

        async def _pdf() -> str:
            conn = await self._get_connection(tab)

            params: dict[str, Any] = {
                "landscape": landscape,
                "paperWidth": paper_width,
                "paperHeight": paper_height,
                "marginTop": margin_top,
                "marginBottom": margin_bottom,
                "marginLeft": margin_left,
                "marginRight": margin_right,
                "printBackground": print_background,
                "scale": scale,
                "preferCSSPageSize": prefer_css_page_size,
            }

            if page_ranges:
                params["pageRanges"] = page_ranges
            if header_template:
                params["displayHeaderFooter"] = True
                params["headerTemplate"] = header_template
            if footer_template:
                params["displayHeaderFooter"] = True
                params["footerTemplate"] = footer_template

            result = await self._send_cdp(
                conn,
                "Page.printToPDF",
                params,
                domains=["Page"],
                timeout=timeout,
            )

            data = result.get("data")
            if data:
                with open(path, "wb") as f:
                    f.write(base64.b64decode(data))
                return path
            raise BrowserError("No PDF data returned")

        return self._run_async(_pdf())

    def get_html(self, tab: Tab | None = None, timeout: float | None = None) -> str:
        """
        Get page outer HTML.

        Args:
            tab: Tab to query (defaults to current)
            timeout: Operation timeout

        Returns:
            HTML string
        """

        async def _html() -> str:
            conn = await self._get_connection(tab)
            result = await self._send_cdp(
                conn,
                "DOM.getDocument",
                domains=["DOM"],
                timeout=timeout,
            )
            root_id = result.get("root", {}).get("nodeId")

            result = await self._send_cdp(
                conn,
                "DOM.getOuterHTML",
                {"nodeId": root_id},
                timeout=timeout,
            )
            return result.get("outerHTML", "")

        return self._run_async(_html())

    def evaluate(
        self, script: str, tab: Tab | None = None, timeout: float | None = None
    ) -> Any:
        """
        Execute JavaScript and return result.

        Args:
            script: JavaScript to execute
            tab: Tab to execute in (defaults to current)
            timeout: Operation timeout

        Returns:
            Script result value
        """

        async def _eval() -> Any:
            conn = await self._get_connection(tab)
            result = await self._send_cdp(
                conn,
                "Runtime.evaluate",
                {"expression": script, "returnByValue": True},
                domains=["Runtime"],
                timeout=timeout,
            )
            # CDP returns {"result": {"type": "...", "value": ...}}
            # _send_cdp extracts "result" key, so result is {"type": ..., "value": ...}
            inner_result = result.get("result", result)
            return inner_result.get("value") if isinstance(inner_result, dict) else None

        return self._run_async(_eval())

    # ─────────────────────────────────────────────────────────────────────────────
    # Cookies
    # ─────────────────────────────────────────────────────────────────────────────

    def get_cookies(
        self, urls: list[str] | None = None, tab: Tab | None = None
    ) -> list[dict]:
        """
        Get all cookies visible to the page.

        Uses CDP Network.getAllCookies to retrieve all cookies for the
        current document's URL, or cookies for specific URLs if provided.

        Args:
            urls: Optional list of URLs to get cookies for
            tab: Tab to query (defaults to current)

        Returns:
            List of cookie dictionaries. Each cookie has:
            - name: Cookie name
            - value: Cookie value
            - domain: Cookie domain
            - path: Cookie path
            - expires: Expiration timestamp (if set)
            - size: Cookie size in bytes
            - httpOnly: Whether cookie is HTTP-only
            - secure: Whether cookie requires HTTPS
            - sameSite: Same-site policy ("Strict", "Lax", or "None")

        Example:
            cookies = browser.get_cookies()
            for c in cookies:
                print(f"{c['name']}: {c['value']}")
        """
        async def _get() -> list[dict]:
            conn = await self._get_connection(tab)
            await self._send_cdp(conn, "Network.enable", domains=["Network"])
            result = await self._send_cdp(conn, "Network.getCookies", {}, domains=["Network"])
            return result.get("cookies", [])

        return self._run_async(_get())

    def set_cookies(
        self,
        cookies: list[dict],
        tab: Tab | None = None,
    ) -> None:
        """
        Set cookies in the browser.

        Args:
            cookies: List of cookie dictionaries. Each cookie should have:
                - name (required): Cookie name
                - value (required): Cookie value
                - url (optional): URL to associate cookie with
                  (derived from current page if missing)
                - domain (optional): Cookie domain
                - path (optional): Cookie path (default "/")
                - secure (optional): Whether cookie requires HTTPS
                - httpOnly (optional): Whether cookie is HTTP-only
                - sameSite (optional): "Strict", "Lax", or "None"
                - expires (optional): Unix timestamp for expiration
            tab: Tab to set cookies for (defaults to current)

        Raises:
            ValueError: If any cookie is missing required 'name' or 'value' keys

        Note:
            CDP requires url or domain. If neither is provided, the cookie's url
            will be automatically derived from the current page's origin.

        Example:
            # With explicit domain
            browser.set_cookies([
                {"name": "session", "value": "abc123", "domain": "example.com"}
            ])

            # Auto-derive from current page
            browser.goto("https://example.com")
            browser.set_cookies([
                {"name": "theme", "value": "dark"}  # url derived from page
            ])
        """
        # Validate required keys
        required = {"name", "value"}
        for i, cookie in enumerate(cookies):
            missing = required - set(cookie.keys())
            if missing:
                raise ValueError(
                    f"Cookie at index {i} missing required key(s): {', '.join(missing)}. "
                    f"Each cookie must have 'name' and 'value'."
                )

        async def _set_cookies() -> None:
            conn = await self._get_connection(tab)

            # Enable Network domain if not already enabled
            await self._send_cdp(conn, "Network.enable", domains=["Network"])

            # Get current page URL for cookies without url/domain
            current_url = None
            for cookie in cookies:
                if "url" not in cookie and "domain" not in cookie:
                    if current_url is None:
                        # Use current tab URL instead of CDP call
                        current_tab = self._get_current_tab()
                        current_url = current_tab.url
                        # CDP needs full URL; if tab is about:blank, derive from connection
                        if current_url in ("about:blank", "chrome://newtab/", ""):
                            # Get from connection's current page
                            result = await self._send_cdp(
                                conn,
                                "Runtime.evaluate",
                                {"expression": "window.location.href"},
                                domains=["Runtime"],
                            )
                            current_url = (
                                result.get("result", {})
                                .get("result", {})
                                .get("value", "")
                            )
                    break

            # Set cookies, adding URL if missing
            for cookie in cookies:
                cookie_copy = dict(cookie)  # Don't modify input
                if "url" not in cookie_copy and "domain" not in cookie_copy:
                    cookie_copy["url"] = current_url
                await self._send_cdp(
                    conn,
                    "Network.setCookie",
                    cookie_copy,
                    domains=["Network"],
                )

        return self._run_async(_set_cookies())

    def delete_cookies(
        self,
        name: str | None = None,
        url: str | None = None,
        domain: str | None = None,
        path: str | None = None,
        tab: Tab | None = None,
    ) -> None:
        """
        Delete cookies matching criteria.

        If no criteria provided, deletes all cookies for the current page.

        Args:
            name: Cookie name to delete (optional)
            url: URL to delete cookies for (optional, derives from current page)
            domain: Domain to delete cookies for (optional)
            path: Path to delete cookies for (optional)
            tab: Tab to delete cookies from (defaults to current)

        Note:
            CDP requires url or domain. If deleting by name only without domain,
            the current page URL is used to scope the deletion.

        Example:
            # Delete specific cookie
            browser.delete_cookies(name="session")

            # Delete all cookies for a domain
            browser.delete_cookies(domain="example.com")

            # Clear all cookies for current page
            browser.delete_cookies()
        """

        async def _delete_cookies() -> None:
            conn = await self._get_connection(tab)

            # Enable Network domain if not already enabled
            await self._send_cdp(conn, "Network.enable", domains=["Network"])

            if name or url or domain or path:
                # Delete specific cookies - use url if domain not provided
                params = {
                    k: v
                    for k, v in {
                        "name": name,
                        "url": url,
                        "domain": domain,
                        "path": path,
                    }.items()
                    if v is not None
                }
                # If name specified but no url/domain, derive from current page
                if name and not (url or domain):
                    current_tab = self._get_current_tab()
                    params["url"] = current_tab.url
                await self._send_cdp(
                    conn,
                    "Network.deleteCookies",
                    params,
                    domains=["Network"],
                )
            else:
                # Clear all cookies for current page
                current_tab = self._get_current_tab()
                current_url = current_tab.url

                # Get all cookies
                result = await self._send_cdp(
                    conn,
                    "Network.getCookies",
                    {"urls": [current_url]},
                    domains=["Network"],
                )
                cookies = result.get("cookies", [])
                for cookie in cookies:
                    await self._send_cdp(
                        conn,
                        "Network.deleteCookies",
                        {"name": cookie["name"], "url": current_url},
                        domains=["Network"],
                    )

        return self._run_async(_delete_cookies())

    # ─────────────────────────────────────────────────────────────────────────────
    # Cookie Export/Import
    # ─────────────────────────────────────────────────────────────────────────────

    def export_cookies(self, file_path: str, tab: Tab | None = None) -> None:
        """
        Export cookies to a JSON file.

        Args:
            file_path: Path to save cookies JSON file
            tab: Tab to export cookies from (defaults to current)

        Example:
            browser.export_cookies("cookies.json")

            # Export from specific tab
            tab = browser.goto("https://example.com")
            browser.export_cookies("example_cookies.json", tab=tab)
        """
        import json

        async def _export() -> None:
            cookies = await self._get_cookies_internal(tab=tab)
            with open(file_path, "w") as f:
                json.dump(cookies, f, indent=2)

        # Don't await - let _run_async handle it
        self._run_async(_export())

    def import_cookies(self, file_path: str, tab: Tab | None = None) -> None:
        """
        Import cookies from a JSON file.

        Args:
            file_path: Path to cookies JSON file
            tab: Tab to import cookies to (defaults to current)

        Example:
            browser.import_cookies("cookies.json")

            # Import to specific tab
            tab = browser.goto("https://example.com")
            browser.import_cookies("example_cookies.json", tab=tab)
        """
        import json

        async def _import() -> None:
            with open(file_path, "r") as f:
                cookies = json.load(f)

            # Validate cookies
            for i, cookie in enumerate(cookies):
                required = {"name", "value"}
                missing = required - set(cookie.keys())
                if missing:
                    raise ValueError(
                        f"Cookie at index {i} missing required key(s): {', '.join(missing)}. "
                        f"Each cookie must have 'name' and 'value'."
                    )

            await self._set_cookies_internal(cookies, tab=tab)

        # Don't await - let _run_async handle it
        self._run_async(_import())

    async def _get_cookies_internal(self, tab: Tab | None = None) -> list[dict]:
        """Internal method to get cookies without wrapping in _run_async."""
        conn = await self._get_connection(tab)
        await self._send_cdp(conn, "Network.enable", domains=["Network"])
        result = await self._send_cdp(conn, "Network.getCookies", {}, domains=["Network"])
        return result.get("cookies", [])

    async def _set_cookies_internal(self, cookies: list[dict], tab: Tab | None = None) -> None:
        """Internal method to set cookies without wrapping in _run_async."""
        conn = await self._get_connection(tab)
        await self._send_cdp(conn, "Network.enable", domains=["Network"])

        # Get current page URL for cookies without url/domain
        current_tab = self._get_current_tab()
        current_url = current_tab.url if current_tab else ""

        for cookie in cookies:
            cookie_copy = dict(cookie)
            if "url" not in cookie_copy and "domain" not in cookie_copy:
                cookie_copy["url"] = current_url
            await self._send_cdp(
                conn,
                "Network.setCookie",
                cookie_copy,
                domains=["Network"],
            )

    # ─────────────────────────────────────────────────────────────────────────────
    # Network Interception
    # ─────────────────────────────────────────────────────────────────────────────

    def on_request(
        self,
        callback: Callable[[dict], None],
        tab: Tab | None = None,
    ) -> None:
        """
        Register callback for network requests.

        Callback receives request params with:
        - requestId: Unique request ID
        - request: {url, method, headers, postData}
        - type: Resource type (Document, Script, XHR, etc.)

        Args:
            callback: Function called with request params
            tab: Tab to monitor (defaults to current)

        Example:
            def log_request(params):
                print(f"→ {params['request']['method']} {params['request']['url']}")

            browser.on_request(log_request)
        """
        self._on_network_event(
            "Network.requestWillBeSent",
            callback,
            tab,
        )

    def on_response(
        self,
        callback: Callable[[dict], None],
        tab: Tab | None = None,
    ) -> None:
        """
        Register callback for network responses.

        Callback receives response params with:
        - requestId: Unique request ID
        - response: {url, status, statusText, headers, mimeType}
        - type: Resource type

        Args:
            callback: Function called with response params
            tab: Tab to monitor (defaults to current)

        Example:
            def log_response(params):
                print(f"← {params['response']['status']} {params['response']['url']}")

            browser.on_response(log_response)
        """
        self._on_network_event(
            "Network.responseReceived",
            callback,
            tab,
        )

    def on_request_failed(
        self,
        callback: Callable[[dict], None],
        tab: Tab | None = None,
    ) -> None:
        """
        Register callback for failed network requests.

        Callback receives failure params with:
        - requestId: Unique request ID
        - errorText: Error description
        - canceled: Whether request was canceled

        Args:
            callback: Function called with failure params
            tab: Tab to monitor (defaults to current)
        """
        self._on_network_event(
            "Network.loadingFailed",
            callback,
            tab,
        )

    def _on_network_event(
        self,
        event: str,
        callback: Callable[[dict], None],
        tab: Tab | None = None,
    ) -> None:
        """Register callback for a network event."""
        # Track callbacks for re-registration
        self._interceptors.setdefault(event, []).append(callback)

        async def _setup() -> None:
            conn = await self._get_connection(tab)
            # Enable Network domain
            await self._send_cdp(conn, "Network.enable")
            # Register listener
            conn.on_event(event, callback)

        # Block until setup complete to ensure Network.enable runs before returning
        self._run_async(_setup())

    async def _reregister_interceptors(self, conn: Connection) -> None:
        """Re-register all network interceptors after reconnect."""
        if not self._interceptors:
            return

        # Enable Network domain
        await self._send_cdp(conn, "Network.enable")
        # Re-register all callbacks
        for event, callbacks in self._interceptors.items():
            for cb in callbacks:
                conn.on_event(event, cb)

    def clear_interceptors(self, tab: Tab | None = None) -> None:
        """
        Clear all registered network interceptors.

        Args:
            tab: Tab to clear interceptors for (defaults to current)
        """
        # Clear in-memory handlers synchronously
        self._interceptors.clear()

        async def _clear() -> None:
            conn = await self._get_connection(tab)
            # Clear event listeners on connection
            conn._event_listeners.clear()

        # Block until clear complete
        self._run_async(_clear())

    # ─────────────────────────────────────────────────────────────────────────────
    # Cleanup
    # ─────────────────────────────────────────────────────────────────────────────

    def _cleanup(self) -> None:
        """Cleanup connections on exit."""
        if self._pool:
            self.close()

    def close(self) -> None:
        """Close all connections and cleanup background tasks."""
        self._interceptors.clear()
        self._interceptor_filters.clear()

        # Disable reconnection before cleanup to prevent new tasks
        self.reconnect_enabled = False

        # Cancel all background reconnection tasks
        if self._reconnect_tasks:
            for task in list(self._reconnect_tasks):
                if not task.done():
                    task.cancel()
            self._reconnect_tasks.clear()

        if self._pool and self._loop:
            try:
                loop = self._loop
                if loop.is_running():
                    # Schedule cleanup to run — cannot await from sync code in a running loop
                    # Use call_soon to ensure it runs before the loop processes more events
                    loop.call_soon(lambda: asyncio.ensure_future(self._pool.close_all()))
                else:
                    loop.run_until_complete(self._pool.close_all())
            except RuntimeError:
                # Event loop may be closed, ignore
                pass

    async def aclose(self) -> None:
        """Async close — properly awaits all cleanup. Use this from async code."""
        self._interceptors.clear()
        self._interceptor_filters.clear()
        self.reconnect_enabled = False

        if self._reconnect_tasks:
            for task in list(self._reconnect_tasks):
                if not task.done():
                    task.cancel()
            self._reconnect_tasks.clear()

        if self._pool:
            await self._pool.close_all()

    async def __aenter__(self) -> Browser:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit — properly awaits cleanup."""
        await self.aclose()

    def __enter__(self) -> Browser:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    def __del__(self) -> None:
        """Cleanup on deletion."""
        try:
            self.close()
        except Exception:
            pass

    def get_stealth_mode(self) -> str:
        """
        Get the current stealth mode level.

        Returns:
            Stealth mode level: "basic", "balanced", or "aggressive"

        Example:
            mode = browser.get_stealth_mode()
            print(f"Stealth mode: {mode}")
        """
        return self._stealth_mode

    def is_stealth(self, tab: Tab | None = None) -> dict[str, Any]:
        """
        Check if stealth mode is working on the current page.

        Evaluates various anti-detection signals to verify the page
        cannot detect automation.

        Args:
            tab: Tab to check (defaults to current tab)

        Returns:
            Dict with detection status:
            {
                'navigator.webdriver': None | bool,
                'webdriver': bool,
                'chrome.runtime': bool,
                'cdc_adoQpoasnfa76pfcZLmcfl_Chart': bool,
                'puppeteer': bool,
            }
        """
        if tab is None:
            tab = self._current_tab

        if tab is None:
            return {
                "error": "No tab available",
                "navigator.webdriver": None,
                "webdriver": None,
                "chrome.runtime": None,
                "cdc_adoQpoasnfa76pfcZLmcfl_Chart": None,
                "puppeteer": None,
            }

        try:
            # Check navigator.webdriver (should be undefined/false in stealth)
            webdriver = self.evaluate("navigator.webdriver", tab=tab)

            # Check window.webdriver (should be falsy in stealth)
            window_webdriver = self.evaluate("window.webdriver", tab=tab)

            # Check chrome.runtime
            has_chrome_runtime = self.evaluate(
                "window.chrome && window.chrome.runtime", tab=tab
            )

            # Check CDP marker
            has_cdc = self.evaluate(
                "window.cdc_adoQpoasnfa76pfcZLmcfl_Chart !== undefined", tab=tab
            )

            # Check Puppeteer
            has_puppeteer = self.evaluate(
                "window.__PuppeteerOverlayObject__ !== undefined || "
                "window.__PuppeteerIsHeadless__ !== undefined",
                tab=tab,
            )

            return {
                "navigator.webdriver": webdriver,
                "webdriver": bool(window_webdriver),
                "chrome.runtime": bool(has_chrome_runtime),
                "cdc_adoQpoasnfa76pfcZLmcfl_Chart": bool(has_cdc),
                "puppeteer": bool(has_puppeteer),
            }
        except Exception as e:
            return {"error": str(e)}
