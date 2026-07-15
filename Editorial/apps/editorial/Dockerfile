# Editorial service (ADR-0008) — daily per-theme "Today's [Topic] Outlook" batch.
# A one-shot batch container: run by a daily cron at the 11:59 AM cut, e.g.
#   docker run --rm --network inkbytes_inkbytes-internal \
#     -e DATABASE_URL=... -e EDITORIAL_LLM_PROVIDER=deepseek \
#     -e EDITORIAL_LLM_BASE_URL=https://api.deepseek.com/v1 \
#     -e EDITORIAL_LLM_MODEL=deepseek-chat -e EDITORIAL_LLM_API_KEY=... \
#     -e DO_SPACES_KEY=... -e DO_SPACES_SECRET=... \
#     inkbytes-editorial --generate
#
# Self-hosted TTS (ADR-0011): Piper (CPU neural TTS) + ffmpeg synthesize the spoken
# column; the EN + ES voice models are baked in below so the batch has no network
# dependency for audio. Zero per-character cost (local-first, like bge-m3).
FROM python:3.12-slim

# ffmpeg = WAV→MP3 transcode; libgomp1 = onnxruntime (Piper) runtime dep; curl to
# fetch the voice models at build time.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Piper voice models (baked in — one voice per language) ────────────────────
# Defaults must match core/config.py TtsCfg.voices. Override the running voices
# via EDITORIAL_TTS_VOICE_EN/_ES only if the matching .onnx is also present here.
ARG PIPER_BASE=https://huggingface.co/rhasspy/piper-voices/resolve/main
RUN mkdir -p /models && cd /models && \
    for rel in \
      en/en_US/ryan/medium/en_US-ryan-medium.onnx \
      en/en_US/ryan/medium/en_US-ryan-medium.onnx.json \
      es/es_MX/ald/medium/es_MX-ald-medium.onnx \
      es/es_MX/ald/medium/es_MX-ald-medium.onnx.json ; do \
        curl -fsSL "$PIPER_BASE/$rel" -o "$(basename "$rel")" ; \
    done

COPY . .
ENTRYPOINT ["python", "main.py", "--config", "env.yaml"]
CMD ["--generate"]
