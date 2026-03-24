# ADR-0002: Runtime.evaluate Result Structure

## Status
Accepted

## Context

CDP Runtime.evaluate returns results in a nested structure:

```json
{
  "result": {
    "result": {
      "type": "string",
      "value": "actual value here"
    }
  }
}
```

The double nesting (result.result.value) is confusing.

## Decision

We handle the full CDP response structure explicitly:

```python
def evaluate(self, script: str) -> Any:
    result = self._send_cdp("Runtime.evaluate", {
        "expression": script,
        "returnByValue": True,
    })
    if "exceptionDetails" in result:
        raise CDPError(...)
    inner = result.get("result", {})
    value = inner.get("result", {}).get("value")
    return value
```

## Consequences

### Positive
- Correct behavior matching CDP specification
- Clear error handling

### Negative
- Confusing API for users expecting simple structure

## References
- [CDP Runtime.evaluate](https://chromedevtools.github.io/devtools-protocol/tot/Runtime/#method-evaluate)
