# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for Quay.

## What is an ADR?

An ADR is a document that captures an important architectural decision, including:

- **Context** — The issue we are facing
- **Decision** — What we decided
- **Consequences** — Trade-offs, benefits, and downsides

## ADR Index

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-accessibility-tree-approach.md) | Accessibility Tree for Element Targeting | Accepted |
| [0002](0002-runtime-evaluate-result-structure.md) | Runtime.evaluate Result Structure | Accepted |
| [0003](0003-callfunctionon-this-binding.md) | Runtime.callFunctionOn this Binding | Accepted |
| [0004](0004-accessibility-node-id.md) | Accessibility Node Backend DOM ID Field | Accepted |
| [0005](0005-nested-async-handling.md) | Nested Async Function Handling | Accepted |

## Creating a New ADR

1. Copy the template and fill in the sections.
2. Update this index.

## Template

```markdown
# ADR-NNNN: Title

## Status
Proposed | Accepted | Deprecated | Superseded

## Context
What is the issue?

## Decision
What did we decide?

## Consequences
What becomes easier or harder?
```
