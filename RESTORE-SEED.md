# RESTORE-SEED — runbook: restore Parham's Hermes state from Telegram-sent backups
#
# Trigger: owner sends `migrate-full.tar.xz` + `hermes-memory-*.tgz` to the bot
# in Telegram and says «برگرد» (or asks to restore from backup).
#
# The agent (Hermes itself) performs the restore:
#
# 1. Download both documents from the chat to a temp dir.
# 2. BASE: extract `migrate-full.tar.xz` into $HERMES_HOME's parent (/data).
#    It contains `.hermes/...` paths. Skip runtime junk:
#    `*.pid *.lock *.log *.heartbeat` and any `cache/` dirs.
# 3. OVERLAY (newer wins): extract `hermes-memory-*.tgz` to temp, then map:
#      memories/  → $HERMES_HOME/memories/        (USER.md, MEMORY.md)
#      scripts/   → $HERMES_HOME/scripts/
#      dollar/    → $HERMES_HOME/dollar/
#      platforms/ → $HERMES_HOME/platforms/       (pairing approvals!)
#      fonts/     → $HERMES_HOME/fonts/
#      state/     → $HERMES_HOME/state/           (session snapshots)
#      skills/    → $HERMES_HOME/skills/          (merge, keep existing)
#      SOUL.md, .env, config.yaml, channel_directory.json,
#      chat_mirror_state.json, pairing_watch_state.json,
#      jobs-manifest.json, dollar_card.py, RESTORE.md → $HERMES_HOME/
#    NOTE: `.env` + `config.yaml` restore ONLY on explicit owner order
#    (they hold secrets + model config). Otherwise keep the live ones.
# 4. Load each § section of memories/USER.md + memories/MEMORY.md into memory.
# 5. Recreate cron jobs from jobs-manifest.json if missing:
#    dollar-hourly, dollar-midnight, memory-backup, pairing-watch
#    (no_agent, deliver=origin, attach_to_session).
# 6. Verify: `python3 -m py_compile` the scripts, confirm pairing approvals
#    list the owner, confirm gateway multiplex + guest profile route intact.
# 7. Restart the gateway so restored state loads, then tell the owner
#    «برگشتم» + what was verified.
