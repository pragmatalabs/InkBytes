# InkBytes TTS microservice (ADR-0011) — Piper + Kokoro over HTTP, on the 16 GB box.
# espeak-ng: g2p (Piper + Kokoro non-English). ffmpeg: WAV→MP3. libsndfile1: soundfile.
# libgomp1: onnxruntime (Piper).
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        espeak-ng ffmpeg libgomp1 libsndfile1 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU-only PyTorch first (avoid the multi-GB CUDA wheel), then the rest.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Piper voices (baked; -high default + -medium for A/B) ─────────────────────
ARG PIPER_BASE=https://huggingface.co/rhasspy/piper-voices/resolve/main
RUN mkdir -p /models && cd /models && \
    for rel in \
      en/en_US/ryan/high/en_US-ryan-high.onnx en/en_US/ryan/high/en_US-ryan-high.onnx.json \
      es/es_MX/claude/high/es_MX-claude-high.onnx es/es_MX/claude/high/es_MX-claude-high.onnx.json \
      en/en_US/ryan/medium/en_US-ryan-medium.onnx en/en_US/ryan/medium/en_US-ryan-medium.onnx.json \
      es/es_MX/ald/medium/es_MX-ald-medium.onnx es/es_MX/ald/medium/es_MX-ald-medium.onnx.json ; do \
        curl -fsSL "$PIPER_BASE/$rel" -o "$(basename "$rel")" ; \
    done

# ── Kokoro: bake the model + pool voices + the English g2p model (no runtime DL) ──
RUN python -m spacy download en_core_web_sm
RUN python - <<'PY'
from kokoro import KPipeline
pools = {"a": ["af_heart","af_bella","am_michael","am_fenrir"], "e": ["ef_dora","em_alex"]}
for lc, voices in pools.items():
    p = KPipeline(lang_code=lc)
    for v in voices:
        list(p("warmup uno dos", voice=v))   # triggers model + voice-pack download into the image
        print("baked kokoro", lc, v, flush=True)
PY

COPY server.py .
EXPOSE 8065
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8065"]
