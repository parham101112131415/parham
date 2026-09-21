#!/bin/sh
# Parham boot: seed → auth → real Hermes dashboard ($PORT) + opencode + bot.
set -e

DATA_DIR="${DATA_DIR:-/data}"
export HERMES_HOME="$DATA_DIR/.hermes"
mkdir -p "$DATA_DIR" "$HERMES_HOME"

# 1. Parham user-theme into the official slot (picked up by /api/dashboard/themes).
mkdir -p "$HERMES_HOME/dashboard-themes"
cp -f /app/theme/dashboard-themes/parham.yaml "$HERMES_HOME/dashboard-themes/parham.yaml"

# 2. opencode Zen auth (free models) — paste local auth.json into OPENCODE_AUTH_JSON.
if [ -n "$OPENCODE_AUTH_JSON" ]; then
  mkdir -p /root/.local/share/opencode
  printf '%s' "$OPENCODE_AUTH_JSON" > /root/.local/share/opencode/auth.json
  chmod 600 /root/.local/share/opencode/auth.json
fi

# 3. Hermes dashboard auth (public bind REQUIRES a provider — basic password).
#     Railway vars DASHBOARD_USER/DASHBOARD_PASS are mapped here.
export HERMES_DASHBOARD_BASIC_AUTH_USERNAME="${DASHBOARD_USER:-admin}"
export HERMES_DASHBOARD_BASIC_AUTH_PASSWORD="${DASHBOARD_PASS:-changeme}"
if [ -z "${HERMES_DASHBOARD_BASIC_AUTH_SECRET:-}" ]; then
  export HERMES_DASHBOARD_BASIC_AUTH_SECRET="parham-local-secret"
fi

# 4. Activate the Parham theme (safe writer — never hand-edit config.yaml).
hermes config set dashboard.theme parham >/dev/null 2>&1 || true

# 5. opencode brain (internal only).
opencode serve --hostname 127.0.0.1 --port 4096 >/data/opencode.log 2>&1 &

# 6. REAL Hermes dashboard on Railway's $PORT (prebuilt UI, no browser here).
hermes dashboard --host 0.0.0.0 --port "${PORT:-8080}" --no-open --skip-build >/data/dashboard.log 2>&1 &

# 7. Telegram bot (polling) in the foreground.
exec python3 -m bot.main
