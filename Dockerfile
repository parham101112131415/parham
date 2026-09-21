# Real Hermes Agent on Railway — nothing custom, nothing cloned.
#
# What runs here is genuine hermes-agent (pinned SHA) with:
#   - Telegram gateway  → TELEGRAM_BOT_TOKEN (+ allowlist)
#   - Brain             → keyless opencode-free, model muse-spark (same family)
#   - Dashboard ($PORT) → real `hermes dashboard` + Parham user-theme
#   - Memory/skills/cron → seeded from your two Hermes backups (secrets stripped)
#
# Secrets are NEVER committed. They arrive only as Railway Variables.
# node:24 — hermes web/ requires node ^22.22 || ^24.11 || >=26 (bookworm python3.11 ✓).
FROM node:24-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HERMES_HOME=/data/.hermes \
    HERMES_ALLOW_ROOT_GATEWAY=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip git ca-certificates curl xz-utils \
    && rm -rf /var/lib/apt/lists/*

# ---- Hermes agent (pinned, upstream) ---------------------------------------
ARG HERMES_REF=593aa74c6182ce2e5e23bc102daaaae71710c05d
RUN git clone --depth 1 --branch main https://github.com/NousResearch/hermes-agent.git /opt/hermes-tmp \
    && cd /opt/hermes-tmp && git fetch --depth 1 origin ${HERMES_REF} && git checkout ${HERMES_REF} \
    && rm -rf /opt/hermes-tmp/.git && mv /opt/hermes-tmp /opt/hermes

# Editable install: upstream blocks wheel/sdist builds (shell/Docker/Nix only),
# but explicitly allows editable installs. Source stays in the image.
RUN pip3 install --break-system-packages -e /opt/hermes
RUN cd /opt/hermes/web && npm install --no-audit --no-fund && npm run build

WORKDIR /app
COPY . .
RUN chmod +x start.sh

EXPOSE 8080
CMD ["./start.sh"]
