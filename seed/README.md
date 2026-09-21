# Seed archives — secrets STRIPPED (safe for this public repo).
#
#   1. migrate-full.tar.xz  — your full `.hermes/` snapshot (base).
#   2. hermes-memory.tgz    — memory overlay from 2026-09-17 (newer wins).
#
# Removed before committing: `.env` files (tokens!), `config.yaml` overlay
# (provisioned fresh at boot), runtime junk (pid/lock/log/heartbeat/cache).
# Secrets arrive ONLY as Railway Variables at runtime — never in git.
