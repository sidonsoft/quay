# ADR-0003: Runtime.callFunctionOn this Binding

## Status
Accepted (v0.2.6 bug fix)

## Context

CDP documentation states: "The object is passed as `this` to the function."

Many implementations incorrectly pass the element as an argument:

```python
# WRONG
self._send_cdp("Runtime.callFunctionOn", {
    "functionDeclaration": "(element) => element.click()",
    "arguments": [{"objectId": object_id}],  # WRONG
})
```

## Decision

The target object is bound to `this`, NOT passed as argument:

```python
# CORRECT
self._send_cdp("Runtime.callFunctionOn", {
    "functionDeclaration": "function() { this.click(); }",
    "objectId": object_id,
    "returnByValue": True,
})
```

## Consequences

### Positive
- Correct behavior following CDP specification
- Simpler arguments

### Negative
- Confusing API for JavaScript developers unfamiliar with CDP

## References
- [CDP Runtime.callFunctionOn](https://chromedevtools.github.io/devtools-protocol/tot/Runtime/#method-callFunctionOn)
