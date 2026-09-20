# Parham — Hermes-style Telegram agent (single image: bot + opencode + dashboard)
FROM node:20-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/data

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip git ca-certificates curl xz-utils \
    && rm -rf /var/lib/apt/lists/*

# opencode (the agent brain — free Zen models like muse-spark)
RUN npm install -g opencode-ai

WORKDIR /app
COPY requirements.txt .
RUN pip3 install --break-system-packages -r requirements.txt

COPY . .
RUN chmod +x start.sh

VOLUME ["/data"]
EXPOSE 8080
CMD ["./start.sh"]
