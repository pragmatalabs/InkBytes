-- 005_embedding_dim_1024.sql
--
-- Switch article embeddings from OpenAI text-embedding-3-small (1536-dim) to the
-- local Ollama bge-m3 model (1024-dim). See Curator ADR-0003.
--
-- Destructive to VECTORS ONLY: existing 1536-dim vectors cannot be cast to
-- 1024-dim, so they are cleared (USING NULL) and the pipeline re-embeds. The
-- source article body_text is untouched, so this is data-safe — only a re-embed
-- pass is required afterwards.
--
-- Guarded in database_service._ensure_schema by an ALTER_GUARD that is TRUE once
-- articles.embedding is already vector(1024), so this file is skipped on
-- subsequent boots.

-- The IVFFlat ANN index is bound to the old vector width; drop before retyping.
DROP INDEX IF EXISTS idx_articles_embedding;

-- Widen-and-clear: discard incompatible 1536-dim data, repopulated at 1024-dim.
ALTER TABLE articles
    ALTER COLUMN embedding TYPE vector(1024) USING NULL::vector(1024);

-- Recreate the cosine ANN index at the new width (lists ~ sqrt(rows); re-tune
-- past 10k rows per ADR-0002).
CREATE INDEX IF NOT EXISTS idx_articles_embedding
    ON articles USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
