# Quay + OpenClaw

Get an OpenClaw agent driving the user's real logged-in Chrome through quay in about five minutes. This is the short path; [MCP Server](mcp.md) has the deeper detail.

## What the agent gets

Once wired up, the agent can call these tools directly: `browser_status`, `open_tab`, `navigate`, `snapshot` (accessibility tree with `axnode@N` refs), `click_text`, `click_ref`, `fill_form`, `evaluate`, `screenshot`, `close_tabs`.

The differentiator versus Playwright MCP or agent-browser: the agent acts inside **the Chrome the user is already signed into** — Gmail, banking, SSO, all working sessions — and sees the **full CDP accessibility tree**, not a simplified snapshot.

## 1. One-time: Chrome ready for debugging

Skip this if the agent already connects fine. Two Chrome rules trip people up:

- **Chrome 136+** ignores `--remote-debugging-port` on the default profile → a separate `--user-data-dir` is mandatory.
- **Chrome 144+** pops a consent prompt for each connection to an already-running Chrome → launching Chrome with the flags avoids it entirely.

```bash
# macOS
open -na "Google Chrome" --args --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.quay/chrome-debug-profile"
```

Or run the launcher shipped with quay (`scripts/chrome-debug.sh` — persistent debug profile, logins survive restarts; sign in once there).

Verify: `curl -s localhost:9222/json/version` should print JSON with `"Browser": "Chrome/…"`.

## 2. Install quay with MCP support

⚠️ **Check the version.** The MCP server ships in **quay 0.2.8+**:

```bash
pip install -U "quay[mcp]"
```

If an older quay is installed, upgrade with `-U`. Confirm: `python -c "import importlib.metadata as m; print(m.version('quay'))"` must be ≥ 0.2.8.

Check where it landed: `which quay`. OpenClaw launches the server itself, but a quick manual smoke test saves debugging later:

```bash
quay --port 9222 version
```

If that prints the Chrome version, quay is working.

## 3. Register with OpenClaw

One command (needs the absolute path if `quay` isn't on the Gateway's PATH):

```bash
openclaw mcp add quay --command quay --arg mcp --arg --port --arg 9222
openclaw mcp doctor quay --probe
```

The probe is the proof — saving a definition doesn't verify anything. A healthy probe lists the 10 tools. If the agent runs under a different user/host than Chrome, use the absolute path: `--command /usr/local/bin/quay`.

GUI alternative: **Settings → MCP → Add server → Stdio**, command `quay`, args `mcp --port 9222`.

## 4. Point the agent at it

Add a line to the agent's AGENTS.md (or workspace instructions):

```markdown
Browser: use quay MCP tools. Loop: browser_status → snapshot → act by
axnode@ ref (click_ref/fill_form) → snapshot again to verify. Chrome must
be running with --remote-debugging-port=9222 (debug profile).
```

That one paragraph is what makes agents *use* the tools instead of ignoring them — the "snapshot → act by ref → verify" loop prevents blind clicking.

## 5. Verify end-to-end

Ask the agent: *"Use your browser tools: open https://example.com, snapshot it, and tell me the page title."*

Expected: `open_tab` → `snapshot` shows `RootWebArea "Example Domain"` → agent reports the title. Done.

## When it doesn't work

| Symptom | Fix |
|---------|-----|
| Probe fails: "Chrome DevTools not reachable" | Chrome isn't running with the flags — do step 1. The error text itself now says what to do. |
| Chrome opens but agent can't connect (Chrome 144+) | Chrome 144 consent prompt: launch *with* the flags (step 1), or enable `chrome://inspect/#remote-debugging` and click Allow on each connect. |
| `quay: command not found` in probe | Use `--command /full/path/to/quay` (find it with `which quay`). |
| Server added but no tools in agent | `openclaw mcp doctor quay --probe` — if it backes off (failed starts retry at 30s→10min doubling), fix the probe first, then reload/retry. |
| `pip install "quay[mcp]"` extra ignored / no mcp support | Old quay cached — `pip install -U "quay[mcp]"` and verify `importlib.metadata.version('quay')` ≥ 0.2.8. |
| Tools present but every call says `Error: …` | Chrome was restarted after the server connected (new tab ids) — re-run `browser_status`; it re-discovers tabs. |

## Security note for OpenClaw setups

`evaluate` means the agent runs arbitrary JavaScript in a real logged-in session. For unattended agents, prefer the dedicated debug profile (step 1) over attaching to the everyday Chrome profile, and consider an OpenClaw tool policy denying `evaluate` while keeping the rest.
