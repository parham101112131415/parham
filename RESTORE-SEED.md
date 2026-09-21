# RESTORE-SEED — runbook: restore Parham's Hermes state from Telegram-sent backups
#
# Trigger: owner sends `migrate-full.tar.xz` + `hermes-memory-*.tgz` to the bot
# in Telegram and says «برگرد» (or asks to restore from backup).
#
# DO NOT improvise the extraction. DO NOT narrate — DO it, step by step:
#
# 1. Download both documents from the chat to a temp dir
#    (e.g. /tmp/restore/). Note their exact paths.
# 2. Run the deterministic restore script (it does base + overlay,
#    newer wins, junk skipped):
#      sh /app/scripts/restore_seed.sh /tmp/restore/migrate-full.tar.xz \
#        /tmp/restore/hermes-memory-*.tgz "$HERMES_HOME"
#    Wait for `RESTORE-DONE`. If it fails, report the exact error and STOP.
# 3. NOTE on secrets: the overlay's `.env` + `config.yaml` restore ONLY on
#    explicit owner order. Otherwise keep the live ones. Say which you kept.
# 4. Load each § section of $HERMES_HOME/memories/USER.md +
#    $HERMES_HOME/memories/MEMORY.md into memory.
# 5. Recreate cron jobs from jobs-manifest.json if missing:
#    dollar-hourly, dollar-midnight, memory-backup, pairing-watch
#    (no_agent, deliver=origin, attach_to_session).
# 6. Verify: `python3 -m py_compile` the scripts, confirm pairing approvals
#    list the owner, confirm gateway multiplex + guest profile route intact.
# 7. Restart the gateway so restored state loads, then tell the owner
#    «برگشتم» + WHAT was verified (files count, jobs, approvals).
#    Never say «دارم بررسی می‌کنم» without doing the next step immediately.
