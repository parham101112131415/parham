# Seed archives (NOT committed)
#
# Put the two Hermes backups here BEFORE first deploy (or upload later
# via dashboard /backup → restore, or Telegram /restore in reply):
#   1. migrate-full.tar.xz          (base — full .hermes snapshot)
#   2. hermes-memory-*.tgz          (overlay — newer wins)
#
# On first boot they are layered onto /data (pid/lock/log/cache skipped),
# then everything saves only on the Railway volume. Nothing stays on the phone.
