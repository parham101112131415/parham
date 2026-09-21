#!/bin/sh
# Deterministic Hermes seed restore: base snapshot + memory overlay (newer wins).
# Used by the agent when the owner sends backup files in Telegram.
# Usage: restore_seed.sh <base.tar.xz> <overlay.tgz> <hermes_home>
set -e
BASE="$1"; OVERLAY="$2"; HOME_DIR="$3"
mkdir -p "$HOME_DIR"
_skip() {
  case "$1" in
    *.pid|*.lock|*.log|*.heartbeat) return 0;;
    */cache/*|*/__pycache__/*) return 0;;
    *) return 1;;
  esac
}
if [ -f "$BASE" ]; then
  tar -tf "$BASE" 2>/dev/null | while read -r m; do
    _skip "$m" || echo "$m"
  done | tar -xJf "$BASE" -C "$(dirname "$HOME_DIR")" -T -
fi
if [ -f "$OVERLAY" ]; then
  _tmp="$(mktemp -d)"
  tar -xzf "$OVERLAY" -C "$_tmp"
  for d in memories scripts dollar platforms fonts state skills; do
    [ -e "$_tmp/$d" ] && cp -r "$_tmp/$d" "$HOME_DIR/"
  done
  for f in SOUL.md .env config.yaml channel_directory.json chat_mirror_state.json pairing_watch_state.json jobs-manifest.json dollar_card.py RESTORE.md; do
    [ -e "$_tmp/$f" ] && cp "$_tmp/$f" "$HOME_DIR/"
  done
  rm -rf "$_tmp"
fi
echo "RESTORE-DONE $(date -u +%FT%TZ)"
