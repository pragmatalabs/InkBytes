# Editorial service (ADR-0008) — daily per-theme "Today's [Topic] Outlook" batch.
# A one-shot batch container: run by a daily cron at the 11:59 AM cut, e.g.
#   docker run --rm --network inkbytes_inkbytes-internal \
#     -e DATABASE_URL=... -e EDITORIAL_LLM_PROVIDER=deepseek \
#     -e EDITORIAL_LLM_BASE_URL=https://api.deepseek.com/v1 \
#     -e EDITORIAL_LLM_MODEL=deepseek-chat -e EDITORIAL_LLM_API_KEY=... \
#     inkbytes-editorial --generate
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENTRYPOINT ["python", "main.py", "--config", "env.yaml"]
CMD ["--generate"]
