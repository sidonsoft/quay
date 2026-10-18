#!/bin/bash
# Launch Chrome with remote debugging enabled

CHROME_PATH="${CHROME_PATH:-$(which google-chrome 2>/dev/null || which chromium 2>/dev/null || echo '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')}"
# Persistent debug profile by default so your logins survive restarts.
# Chrome 136+ ignores --remote-debugging-port on the default profile, so a
# separate --user-data-dir is required; Chrome 144+ consent prompts are skipped
# when Chrome is launched with these flags.
PROFILE_DIR="${PROFILE_DIR:-$HOME/.quay/chrome-debug-profile}"
mkdir -p "$PROFILE_DIR"
PORT="${PORT:-9222}"

echo "Starting Chrome with remote debugging on port $PORT..."
echo "Profile directory: $PROFILE_DIR"

"$CHROME_PATH" \
  --remote-debugging-port=$PORT \
  --user-data-dir="$PROFILE_DIR" \
  --no-first-run \
  --no-default-browser-check \
  "$@"
