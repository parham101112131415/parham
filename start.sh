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
  if [ -f /app/seed/hermes-memory-20260917-1405.tgz ]; then
    _tmp="$(mktemp -d)"
    tar -xzf /app/seed/hermes-memory-20260917-1405.tgz -C "$_tmp"
    for d in memories scripts dollar platforms fonts state skills; do
      [ -e "$_tmp/$d" ] && cp -r "$_tmp/$d" "$HERMES_HOME/"
    done
    for f in SOUL.md .env config.yaml channel_directory.json chat_mirror_state.json pairing_watch_state.json jobs-manifest.json dollar_card.py RESTORE.md; do
      [ -e "$_tmp/$f" ] && cp "$_tmp/$f" "$HERMES_HOME/"
    done
    rm -rf "$_tmp"
  fi
  date -u > "$DATA_DIR/.seeded"
fi

# 2. opencode engine auth (optional): paste local auth.json content into
#    OPENCODE_AUTH_JSON. Free tier usually works in the genuine client as-is.
if [ -n "$OPENCODE_AUTH_JSON" ]; then
  mkdir -p /root/.local/share/opencode
  printf '%s' "$OPENCODE_AUTH_JSON" > /root/.local/share/opencode/auth.json
  chmod 600 /root/.local/share/opencode/auth.json
fi

# 3. Invisible driver: genuine opencode CLI as a local OpenAI API.
#    Hermes stays 100% stock (provider=custom) — engine = opencode = me.
export OPENCODE_MODEL="${OPENCODE_MODEL:-opencode/muse-spark-1.3-contributor-free}"
export OPENCODE_PROXY_PORT="4096"
export OPENCODE_TIMEOUT="${OPENCODE_TIMEOUT:-900}"
python3 /app/proxy/server.py >/data/proxy.log 2>&1 &
echo "[boot] proxy starting on 127.0.0.1:4096 model=$OPENCODE_MODEL"
for _i in $(seq 1 30); do
  if curl -sf -m 2 http://127.0.0.1:4096/v1/models >/dev/null 2>&1; then
    echo "[boot] proxy UP"
    break
  fi
  sleep 2
done
curl -s -m 5 http://127.0.0.1:4096/v1/models || echo "[boot] proxy NOT reachable!"

# 4. Point Hermes at the local engine. Safe writers only (output kept visible).
echo "[boot] hermes: $(which hermes)"
hermes config set providers.custom.base_url "http://127.0.0.1:4096/v1" || echo "[boot] WARN: base_url set failed"
hermes config set providers.custom.api_key "parham-local" || echo "[boot] WARN: api_key set failed"
hermes config set model.default "custom/muse-spark-1.3" || echo "[boot] WARN: model set failed"
hermes config set model.context_length 1000000 || echo "[boot] WARN: context_length set failed"
hermes config set custom_providers '[{"base_url":"http://127.0.0.1:4096/v1","models":{"muse-spark-1.3":{"context_length":1000000}}}]' || echo "[boot] WARN: custom_providers set failed"
hermes config set providers.custom.request_timeout_seconds 600 || echo "[boot] WARN: timeout set failed"
hermes config set providers.custom.stale_timeout_seconds 600 || echo "[boot] WARN: stale timeout set failed"
echo "[boot] effective model: $(hermes config get model.default 2>&1)"

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
