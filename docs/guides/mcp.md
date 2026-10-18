# MCP Server

`quay mcp` runs a [Model Context Protocol](https://modelcontextprotocol.io) server over stdio, letting MCP-capable agents (Claude Code, Codex, OpenClaw, any MCP client) drive the user's real, logged-in Chrome through quay.

## Install

```bash
pip install "quay[mcp]"
```

The `mcp` extra pulls the official Python SDK (mcp 2.x). It is optional — the core package stays dependency-light.

## Run

```bash
quay mcp                 # Chrome on localhost:9222
quay mcp --port 9333     # custom port (flags also accepted after `mcp`)
```

The server speaks JSON-RPC over stdio, so you don't run it directly in a terminal — MCP client configs spawn it. It connects to Chrome at startup; Chrome must already be running with remote debugging (see [Installation](../installation.md), including the Chrome 136+/144+ notes).

## Tools

| Tool | Purpose |
|------|---------|
| `browser_status` | Chrome version + open tabs (ids, titles, URLs) |
| `open_tab` | Open a new tab at a URL |
| `navigate` | Navigate the current tab |
| `snapshot` | Accessibility tree; interactive nodes carry refs (`axnode@N`) |
| `click_text` | Click first element containing visible text |
| `click_ref` | Click by AX ref from `snapshot` (precise) |
| `fill_form` | Fill fields by label/name (JSON object) |
| `evaluate` | Run JavaScript, return result |
| `screenshot` | Save PNG on the server machine, return path |
| `close_tabs` | Close tab ids or all non-`chrome://` tabs |

Agents are told (via server `instructions`) to loop: status → open/navigate → snapshot → act by ref → snapshot to verify.

## Client configuration

Claude Code (`~/.claude.json` or project `.mcp.json`):

```json
{
  "mcpServers": {
    "quay": {
      "command": "quay",
      "args": ["mcp", "--port", "9222"]
    }
  }
}
```

Codex (`~/.codex/config.toml`):

```toml
[mcp_servers.quay]
command = "quay"
args = ["mcp", "--port", "9222"]
```

Any stdio MCP client works — the pattern is `command: quay, args: ["mcp"]`.

## Notes and limits

- **One Browser per server**: the server keeps a single `Browser` instance with a dedicated event-loop thread; concurrent tool calls are executed sequentially by the MCP client per session.
- **Errors are text**: tool failures return `Error: ...` strings rather than protocol errors, so agents can read and react.
- **Screenshots are server-side paths**: the agent gets a local file path on the machine running the server.
- **Security**: the agent can run arbitrary JavaScript (`evaluate`) in your real logged-in session — treat it like handing someone your browser. Point clients at a dedicated debug profile if that's too broad.

## Testing

Unit tests (no Chrome needed):

```bash
pytest tests/test_mcp_server.py
```

Live smoke test:

```bash
./scripts/chrome-debug.sh &
echo '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}' | quay mcp
```
