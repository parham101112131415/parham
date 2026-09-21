# Parham — real Hermes dashboard + Telegram agent bot + opencode brain.
#
# Surfaces:
#   $PORT → genuine `hermes dashboard` (pinned SHA, Parham user-theme)
#   Telegram → bot (polling) bridged to internal `opencode serve :4096`
#
# All state lives on the Railway Volume mounted at /data. Nothing on the phone.
FROM node:20-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/data \
    HERMES_HOME=/data/.hermes

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv git ca-certificates curl xz-utils \
    && rm -rf /var/lib/apt/lists/*

# ---- Hermes agent (pinned) + Parham theme --------------------------------
ARG HERMES_REF=593aa74c6182ce2e5e23bc102daaaae71710c05d
RUN git clone --depth 1 --branch main https://github.com/NousResearch/hermes-agent.git /opt/hermes-tmp \
    && cd /opt/hermes-tmp && git fetch origin ${HERMES_REF} && git checkout ${HERMES_REF} \
    && rm -rf /opt/hermes-tmp/.git && mv /opt/hermes-tmp /opt/hermes
COPY theme/web-patches/index.html /opt/hermes/web/index.html
RUN pip3 install --break-system-packages /opt/hermes
RUN cd /opt/hermes/web && npm ci --no-audit --no-fund && npm run build

# ---- opencode brain (free Zen models) ------------------------------------
ARG OPENCODE_VERSION=1.18.27
RUN npm install -g opencode-ai@${OPENCODE_VERSION} --no-audit --no-fund

# ---- Parham bot ------------------------------------------------------------
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --break-system-packages -r requirements.txt
COPY . .

RUN chmod +x start.sh
EXPOSE 8080
CMD ["./start.sh"]
