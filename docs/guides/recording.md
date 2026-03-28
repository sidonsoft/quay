# Session Recording and Playback

Quay supports recording and replaying browser sessions for testing, debugging, and automation.

> **⚠️ Known Issues**
>
> See [Changelog](../changelog.md) for current bugs and limitations. Playback validates actions against a whitelist of allowed operations for security.

## Recording a Session

To record a session, use `start_recording()` and `stop_recording()`. Actions performed during this period are captured and serialized to JSON.

```python
from quay import Browser

browser = Browser()
browser.start_recording("login_flow.json")

browser.goto("https://example.com/login")
browser.type_by_name("username", "user@example.com")
browser.type_by_name("password", "secret")
browser.click_by_text("Sign In")

browser.stop_recording()  # Saves to login_flow.json
```

## Playing Back

To replay a previously recorded session, use `playback()`.

```python
from quay import Browser

browser = Browser()
# Replay at double speed with verification enabled
browser.playback("login_flow.json", speed=2.0, verify=True)
```

## Use Cases

| Use Case | Benefit |
|----------|---------|
| **Regression testing** | Replay user journeys after UI changes to ensure they still work. |
| **Bug reports** | Share a JSON recording with developers to provide perfectly reproducible steps. |
| **Demo automation** | Record a complex demo once and replay it reliably on demand. |
| **CI/CD integration** | Automate complex login or navigation flows without writing code for every step. |

## Controls

You can pause and resume recording if you need to perform actions that should not be captured.

```python
browser.start_recording("workflow.json")

browser.goto("https://example.com/start")
browser.pause_recording()
# These actions are NOT recorded
browser.snapshot()
browser.screenshot("setup.png")
browser.resume_recording()

browser.click_by_text("Continue")
browser.stop_recording()
```

## Recording Format

Recordings are saved as standard JSON files.

```json
{
  "version": "1.0",
  "quay_version": "0.4.1",
  "recorded_at": "2026-03-24T12:00:00.000000",
  "actions": [
    {
      "type": "goto",
      "timestamp": 0.0,
      "url": "https://example.com"
    },
    {
      "type": "type_by_name",
      "timestamp": 1.25,
      "name": "username",
      "text": "REDACTED"
    }
  ],
  "metadata": {
    "total_duration": 1.25,
    "action_count": 2
  }
}
```

## Verification Mode

When `verify=True` is passed to `playback()`, the browser will check the return value of every action. If an action fails, a `BrowserError` is raised.

When `verify=False` (default), playback will continue even if some actions fail.
