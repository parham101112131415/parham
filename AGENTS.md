# Parham — Telegram gateway workdir notes (auto-loaded every turn)

- Owner ID: 8055210419. Reply in the user's own language (Persian default).
- `$HERMES_HOME` persists on the Railway volume. `/app` is the ephemeral image.
- BACKUP RESTORE (do it, don't narrate it): when the owner sends backup
  archives (`migrate-full.tar.xz` + `hermes-memory-*.tgz`) and says
  «برگرد» (or asks to restore), download both to `/tmp/restore/` and run:
    sh /app/scripts/restore_seed.sh /tmp/restore/migrate-full.tar.xz /tmp/restore/hermes-memory-*.tgz "$HERMES_HOME"
  Then continue with `/app/RESTORE-SEED.md` steps 3–7 (memory load, cron
  recreate, verify, gateway restart, report). Never reply with only an
  acknowledgement — execute with tools FIRST, then report counts.
