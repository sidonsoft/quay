#!/bin/bash
# Launch Chrome with remote debugging enabled

CHROME_PATH="${CHROME_PATH:-$(which google-chrome 2>/dev/null || which chromium 2>/dev/null || echo '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')}"
PROFILE_DIR="${PROFILE_DIR:-$(mktemp -d)}"
PORT="${PORT:-9222}"

echo "Starting Chrome with remote debugging on port $PORT..."
echo "Profile directory: $PROFILE_DIR"

"$CHROME_PATH" \
  --remote-debugging-port=$PORT \
  --user-data-dir="$PROFILE_DIR" \
  --no-first-run \
  --no-default-browser-check \
  "$@"
