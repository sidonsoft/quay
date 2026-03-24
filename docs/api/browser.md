# Browser API Reference

The main entry point for browser automation.

## Constructor

```python
from quay import Browser

browser = Browser(
    host="localhost",
    port=9222,
    timeout=30.0,
    reconnect=True,
    reconnect_max_retries=5,
    reconnect_backoff=0.5,
    reconnect_callback=None,
)
```

## Tab Management

### list_tabs()
List all open tabs. Returns `list[Tab]`.
```python
tabs = browser.list_tabs()
```

### new_tab()
Create a new tab. Returns `Tab`.
```python
tab = browser.new_tab("https://example.com")
```

### activate_tab()
Switch to a tab.
```python
browser.activate_tab(tab)
```

### close_tab()
Close a tab.
```python
browser.close_tab(tab)
```

### temp_tab()
Context manager for isolated workflows. Auto-closes on exit.
```python
with browser.temp_tab("https://example.com") as tab:
    browser.click_by_text("Submit")
# Tab auto-closed
```

### switch_to_tab()
Switch to a tab, returns previous tab for easy switching back.
```python
previous = browser.switch_to_tab(tab1)
browser.switch_to_tab(previous)
```

## Navigation

### navigate(url, tab=None, timeout=None)
Navigate to URL. Returns bool.
```python
browser.navigate("https://example.com")
```

### wait_for_load_state(state="load", timeout=None)
Wait for page load state: "load", "DOMContentLoaded", "complete".
```python
browser.wait_for_load_state("complete")
```

## Accessibility Tree

### accessibility_tree(tab=None)
Get AXNode tree. Returns `AXNode`.
```python
tree = browser.accessibility_tree()
print(tree.to_tree_str())
buttons = tree.find_by_role("button")
elements = tree.find_by_name("Submit")
node = tree.find("42")
```

## Click

### click(ref, tab=None, timeout=None, double=False, button="left")
Click element by ref. Returns bool.
```python
browser.click("42")
browser.click("42", double=True)
browser.click("42", button="right")
```

### click_by_text(text, tab=None, timeout=None)
Click by visible text. Returns bool.
```python
browser.click_by_text("Sign in")
```

## Type

### type_text(ref, text, tab=None, timeout=None)
Type into element by ref. Returns bool.
```python
browser.type_text("42", "Hello")
```

### type_by_name(name, text, tab=None, timeout=None)
Type by label/placeholder/name. Returns bool.
```python
browser.type_by_name("Email", "user@example.com")
```

### type_slowly(ref, text, delay=0.05, tab=None, timeout=None)
Type character by character. Returns bool.
```python
browser.type_slowly("42", "Hello", delay=0.1)
```

## Keyboard

### press_key(key, modifiers=None, tab=None, timeout=None)
Press key. Modifiers: Control, Shift, Alt, Meta.
```python
browser.press_key("Enter")
browser.press_key("c", modifiers=["Control"])
```

## Mouse

### hover(ref, tab=None, timeout=None)
Hover over element. Returns bool.
```python
browser.hover("42")
```

## Form Filling

### fill_form(fields, tab=None, timeout=None, raise_on_error=False)
Fill form fields. Returns dict[str, bool].
```python
browser.fill_form({"Email": "a@b.com", "Password": "secret"})
```

## Wait Conditions

### wait_for(selector=None, text=None, url=None, timeout=10.0)
Wait for condition. Returns bool.
```python
browser.wait_for(selector="#loading")
browser.wait_for(text="Welcome")
browser.wait_for(url="https://example.com/success")
```

### wait_until(condition, timeout=10.0, interval=0.1)
Wait for custom condition.
```python
browser.wait_until(lambda: browser.evaluate("document.readyState") == "complete")
```

## Content

### get_html(tab=None)
Get page HTML. Returns str.
```python
html = browser.get_html()
```

### evaluate(script, tab=None, timeout=None)
Execute JavaScript. Returns Any.
```python
title = browser.evaluate("document.title")
```

### screenshot(path, tab=None, timeout=None)
Save screenshot. Returns bool.
```python
browser.screenshot("/tmp/page.png")
```

### pdf(path, tab=None, timeout=None, **kwargs)
Generate PDF. Returns str path.
```python
browser.pdf("output.pdf", landscape=True, print_background=True)
```

## Cookies

### get_cookies(urls=None, tab=None)
Get cookies. Returns list[dict].
```python
cookies = browser.get_cookies()
```

### set_cookies(cookies, tab=None)
Set cookies.
```python
browser.set_cookies([{"name": "session", "value": "abc", "domain": ".example.com"}])
```

### delete_cookies(name=None, url=None, domain=None, path=None, tab=None)
Delete cookies.
```python
browser.delete_cookies("session")
browser.delete_cookies()
```

## Network

### on_request(callback, tab=None)
Monitor requests.
```python
browser.on_request(lambda req: print(req['request']['url']))
```

### on_response(callback, tab=None)
Monitor responses.
```python
browser.on_response(lambda res: print(res['response']['status']))
```

### on_request_failed(callback, tab=None)
Monitor failed requests.
```python
browser.on_request_failed(lambda req: print(f"Failed: {req}"))
```

### clear_interceptors(tab=None)
Clear all interceptors.
```python
browser.clear_interceptors()
```

## Connection

### is_connected()
Check if connected. Returns bool.
```python
if browser.is_connected(): print("Connected")
```

### close()
Close connection.
```python
browser.close()
```

## Recording & Playback

### start_recording(path=None)
Start recording. Returns Recording.
```python
recording = browser.start_recording("session.json")
```

### stop_recording()
Stop and save. Returns str path.
```python
path = browser.stop_recording()
```

### playback(recording, speed=1.0, verify=False)
Replay session. Returns bool.
```python
browser.playback("session.json", speed=2.0, verify=True)
```

### pause_recording() / resume_recording()
Pause/resume recording.

### get_recording()
Get current Recording or None.

## Visual Regression

### compare_screenshots(baseline, current, threshold=0.0, output_diff=None, region=None)
Compare screenshots. Returns ComparisonResult.
```python
result = browser.compare_screenshots("baseline.png", "current.png")
```

### screenshot_and_compare(path, baseline, threshold=0.0, output_diff=None, region=None)
Take and compare. Returns ComparisonResult.

### assert_visual_match(baseline, threshold=0.0, update_baseline=False, region=None)
Assert match. Raises AssertionError if mismatch.
```python
browser.assert_visual_match("baseline.png", threshold=0.01)
```
