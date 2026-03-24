# ADR-0004: Accessibility Node Backend DOM ID Field

## Status
Accepted (v0.2.6 bug fix)

## Context

CDP specification defines the field as `backendDOMNodeId`:

```json
{
  "backendDOMNodeId": 123
}
```

Common mistakes:
- `backendNodeId` — shortened version (incorrect)
- `backend_node_id` — Python convention (incorrect)
- `backendDOMNodeId` — CDP specification (correct)

## Decision

Always use `backendDOMNodeId` exactly as defined in CDP:

```python
backend_node_id = node.get("backendDOMNodeId")  # Correct

result = await self._send_cdp("DOM.resolveNode", {
    "backendNodeId": backend_node_id,  # Note: DOM.resolveNode uses backendNodeId
})
```

Note: `DOM.resolveNode` uses `backendNodeId` but accessibility nodes use `backendDOMNodeId`.

## References
- [CDP Accessibility.Node](https://chromedevtools.github.io/devtools-protocol/tot/Accessibility/#type-Node)
- [CDP DOM.resolveNode](https://chromedevtools.github.io/devtools-protocol/tot/DOM/#method-resolveNode)
