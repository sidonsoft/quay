# ADR-0005: Nested Async Function Handling

## Status
Accepted (v0.2.6 bug fix)

## Context

Python coroutines and Tasks are different types:

```python
# Coroutine
coro = my_func()  # <coroutine object>

# Task
task = asyncio.create_task(my_func())  # <Task>
```

When checking return values, it is easy to confuse them:

```python
# WRONG: Returns coroutine, not bool
if check():  # Always truthy
    ...

# CORRECT: Await first
result = await check()
if result:
    ...
```

## Decision

Always handle async return values correctly:

```python
# CORRECT: Await before checking
async def _execute_script(self, script: str) -> bool:
    try:
        result = await self._send_cdp(...)  # Await
        return bool(result)
    except Exception:
        return False
```

## Consequences

### Positive
- Correct boolean checks
- Prevents silent bugs

### Negative
- Verbosity — need intermediate variable
- Easy mistake — forgetting await

## References
- [Python Asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
- [PEP 492 — Coroutines](https://peps.python.org/pep-0492/)
