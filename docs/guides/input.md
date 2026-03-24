# Keyboard & Mouse

Quay provides keyboard input and mouse actions.

## Keyboard Input

### press_key()

Press a key or key combination:

```python
# Single key
browser.press_key("Enter")
browser.press_key("Tab")
browser.press_key("Escape")

# Key combinations
browser.press_key("a", modifiers=["Control"])  # Ctrl+A (select all)
browser.press_key("c", modifiers=["Control"])  # Ctrl+C (copy)
browser.press_key("v", modifiers=["Control"])  # Ctrl+V (paste)
browser.press_key("s", modifiers=["Control"])  # Ctrl+S (save)
browser.press_key("Enter", modifiers=["Shift"])  # Shift+Enter

# Special keys
browser.press_key("ArrowDown")
browser.press_key("ArrowUp")
browser.press_key("PageDown")
browser.press_key("Home")
browser.press_key("End")
browser.press_key("Delete")
browser.press_key("Backspace")
```

### type_slowly()

Type text character by character with delay:

```python
# Type with default delay (0.05s per character)
browser.type_slowly("email-input", "user@example.com")

# Type faster
browser.type_slowly("search-box", "query", delay=0.01)

# Type slower (like human)
browser.type_slowly("message", "Hello, world!", delay=0.1)
```

### type_text()

Type text instantly into an element:

```python
# Type by accessibility ref
browser.type_text("42", "Hello")

# Type into focused element
browser.press_key("Tab")
browser.type_text(None, "some text")  # Uses focused element
```

## Mouse Actions

### click()

Click an element:

```python
# Click by accessibility ref
browser.click("42")

# Click by text
browser.click_by_text("Submit")

# Double-click
browser.click("42", double=True)

# Right-click
browser.click("42", button="right")

# Click with specific tab
browser.click("42", tab=tab)
```

### hover()

Hover over an element:

```python
# Hover by accessibility ref
browser.hover("42")

# Hover by finding element first
tree = browser.accessibility_tree()
button = tree.find_by_role("button")[0]
browser.hover(button.ref)
```

### Form Interaction

```python
# Fill form fields
browser.fill_form({
    "Name": "John Doe",
    "Email": "john@example.com",
    "Password": "secret123"
})

# Submit form
browser.press_key("Enter")

# Or click submit button
browser.click_by_text("Sign Up")
```

## Advanced Usage

### Keyboard Navigation

```python
# Navigate with Tab
for i in range(5):
    browser.press_key("Tab")

# Select from dropdown
browser.press_key("ArrowDown")
browser.press_key("ArrowDown")
browser.press_key("Enter")
```

### Drag and Drop

Currently not directly supported. Use JavaScript:

```python
browser.evaluate('''
const source = document.querySelector("#item");
const target = document.querySelector("#drop-zone");
source.dispatchEvent(new DragEvent("dragstart"));
target.dispatchEvent(new DragEvent("drop"));
''')
```

### File Upload

```python
# Use type_text with file input
browser.type_text("file-input", "/path/to/file.txt")
```
