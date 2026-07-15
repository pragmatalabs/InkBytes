"""DigitalOcean Spaces (S3) uploader for editorial audio (ADR-0011).

A thin boto3 wrapper: upload MP3 bytes public-read and return the public URL. The
Messor package has a richer handler, but it returns a bool (no URL) and lives in a
different service; a ~30-line self-contained uploader keeps Editorial dependency-
light and owns the URL construction the callers actually need.

`configured` is False when key/secret are blank — the caller then skips synthesis
entirely rather than failing the batch (TTS is best-effort).
"""
from __future__ import annotations

import logging

from core.config import SpacesCfg

logger = logging.getLogger(__name__)


class SpacesStorage:
    def __init__(self, cfg: SpacesCfg) -> None:
        self.cfg = cfg
        self._client = None  # lazy — don't import boto3 / open a client when disabled

    @property
    def configured(self) -> bool:
        return bool(self.cfg.key and self.cfg.secret and self.cfg.bucket)

    def _client_or_init(self):
        if self._client is None:
            import boto3  # local import: only when TTS is actually enabled
            self._client = boto3.client(
                "s3",
                endpoint_url=self.cfg.endpoint,
                region_name=self.cfg.region,
                aws_access_key_id=self.cfg.key,
                aws_secret_access_key=self.cfg.secret,
            )
        return self._client

    def public_url(self, key: str) -> str:
        base = self.cfg.public_base.rstrip("/") if self.cfg.public_base \
            else f"{self.cfg.endpoint.rstrip('/')}/{self.cfg.bucket}"
        return f"{base}/{key.lstrip('/')}"

    def upload_bytes(self, data: bytes, key: str,
                     content_type: str = "audio/mpeg") -> str:
        """Upload public-read; return the public URL. Raises on failure (the caller
        wraps it — a failed upload must not abort the text batch)."""
        self._client_or_init().put_object(
            Bucket=self.cfg.bucket, Key=key.lstrip("/"), Body=data,
            ACL="public-read", ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable")
        url = self.public_url(key)
        logger.info("uploaded audio → %s (%d bytes)", url, len(data))
        return url
