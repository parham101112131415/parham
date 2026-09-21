#!/bin/sh
# Parham boot: seed Hermes state → provision model+theme → dashboard + gateway.
# Everything lives on the Railway Volume ($DATA_DIR). Nothing on the phone.
set -e

DATA_DIR="${DATA_DIR:-/data}"
export HERMES_HOME="$DATA_DIR/.hermes"
mkdir -p "$DATA_DIR" "$HERMES_HOME"

# 1. Seed (first boot only): full snapshot, then memory overlay (newer wins).
if [ ! -f "$DATA_DIR/.seeded" ]; then
  if [ -f /app/seed/migrate-full.tar.xz ]; then
    tar -xJf /app/seed/migrate-full.tar.xz -C "$DATA_DIR"
  fi
  if [ -f /app/seed/hermes-memory.tgz ]; then
    _tmp="$(mktemp -d)"
    tar -xzf /app/seed/hermes-memory.tgz -C "$_tmp"
    for d in memories scripts dollar platforms fonts state skills; do
      [ -e "$_tmp/$d" ] && cp -r "$_tmp/$d" "$HERMES_HOME/"
    done
    for f in SOUL.md channel_directory.json chat_mirror_state.json pairing_watch_state.json jobs-manifest.json dollar_card.py RESTORE.md; do
      [ -e "$_tmp/$f" ] && cp "$_tmp/$f" "$HERMES_HOME/"
    done
    rm -rf "$_tmp"
  fi
  date -u > "$DATA_DIR/.seeded"
fi

# 2. Brain = keyless opencode-free, muse-spark 1.3 (runs on me).
#    Safe writer only — never hand-edit config.yaml.
hermes config set model.default "opencode-free/muse-spark-1.3-contributor-free" >/dev/null 2>&1 || true

# 4. Dashboard auth (a public bind REQUIRES a provider — basic password).
export HERMES_DASHBOARD_BASIC_AUTH_USERNAME="${DASHBOARD_USER:-admin}"
export HERMES_DASHBOARD_BASIC_AUTH_PASSWORD="${DASHBOARD_PASS:-changeme}"
if [ -z "${HERMES_DASHBOARD_BASIC_AUTH_SECRET:-}" ]; then
  export HERMES_DASHBOARD_BASIC_AUTH_SECRET="parham-local-secret"
fi

# 5. Real Hermes dashboard on Railway's $PORT (prebuilt UI, no browser here).
hermes dashboard --host 0.0.0.0 --port "${PORT:-8080}" --no-open --skip-build >/data/dashboard.log 2>&1 &

# 6. Real Hermes gateway (Telegram) in the foreground — container lives with it.
exec hermes gateway run --replace
