# InkBytes TTS microservice (ADR-0011) — Piper synthesis over HTTP, on the 16 GB box.
# ffmpeg = WAV→MP3; libgomp1 = onnxruntime runtime dep; curl fetches the voices.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Voice models baked in (must match TTS_VOICE_EN/_ES / the Editorial config defaults).
ARG PIPER_BASE=https://huggingface.co/rhasspy/piper-voices/resolve/main
RUN mkdir -p /models && cd /models && \
    for rel in \
      en/en_US/ryan/high/en_US-ryan-high.onnx \
      en/en_US/ryan/high/en_US-ryan-high.onnx.json \
      es/es_MX/claude/high/es_MX-claude-high.onnx \
      es/es_MX/claude/high/es_MX-claude-high.onnx.json \
      en/en_US/ryan/medium/en_US-ryan-medium.onnx \
      en/en_US/ryan/medium/en_US-ryan-medium.onnx.json \
      es/es_MX/ald/medium/es_MX-ald-medium.onnx \
      es/es_MX/ald/medium/es_MX-ald-medium.onnx.json ; do \
        curl -fsSL "$PIPER_BASE/$rel" -o "$(basename "$rel")" ; \
    done

COPY server.py .
EXPOSE 8065
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8065"]
