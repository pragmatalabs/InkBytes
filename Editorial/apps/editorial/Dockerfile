# Editorial service (ADR-0008) — daily per-theme "Today's [Topic] Outlook" batch.
# A one-shot batch container, run by a daily cron at the 11:59 AM cut, e.g.
#   docker run --rm --network inkbytes_inkbytes-internal \
#     -e DATABASE_URL=... -e EDITORIAL_LLM_PROVIDER=deepseek ... \
#     -e DO_SPACES_KEY=... -e DO_SPACES_SECRET=... \
#     -e EDITORIAL_TTS_URL=https://tts.inkbytes.news -e EDITORIAL_TTS_SECRET=... \
#     inkbytes-editorial --generate
#
# TTS (ADR-0011): synthesis is REMOTE — the batch POSTs text to the Piper microservice
# on the 16 GB box (Editorial/apps/tts-server) and uploads the returned MP3 to Spaces.
# So this image stays slim (no Piper/ffmpeg/voice models): the droplet has no RAM for
# onnxruntime. For local synthesis in dev, leave EDITORIAL_TTS_URL unset and install
# piper-tts + ffmpeg in your venv.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENTRYPOINT ["python", "main.py", "--config", "env.yaml"]
CMD ["--generate"]
