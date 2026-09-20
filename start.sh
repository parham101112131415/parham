#!/bin/sh
set -e
mkdir -p "$DATA_DIR"

# opencode Zen auth: paste your local ~/.local/share/opencode/auth.json
# content into the OPENCODE_AUTH_JSON variable (one line). Written here
# so free models (muse-spark, ...) work without a browser login.
if [ -n "$OPENCODE_AUTH_JSON" ]; then
  mkdir -p /root/.local/share/opencode
  printf '%s' "$OPENCODE_AUTH_JSON" > /root/.local/share/opencode/auth.json
  chmod 600 /root/.local/share/opencode/auth.json
fi

# 1. opencode brain (internal only)
opencode serve --hostname 127.0.0.1 --port 4096 >/data/opencode.log 2>&1 &

# 2. bot + workers + dashboard (dashboard on Railway $PORT)
exec python3 -m bot.main
