CREATE TABLE IF NOT EXISTS bot_settings (
    key text PRIMARY KEY,
    value text NOT NULL,
    updated_by text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS lawyer_materials (
    id bigserial PRIMARY KEY,
    title text NOT NULL,
    language text NOT NULL DEFAULT 'ru' CHECK (language IN ('ru','kk')),
    content text NOT NULL,
    uploaded_by text NOT NULL,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    search_vector tsvector GENERATED ALWAYS AS (to_tsvector('simple', title || ' ' || content)) STORED
);
CREATE INDEX IF NOT EXISTS lawyer_search_idx ON lawyer_materials USING gin(search_vector);
ALTER TABLE knowledge_embeddings DROP CONSTRAINT IF EXISTS knowledge_embeddings_kind_check;
ALTER TABLE knowledge_embeddings ADD CONSTRAINT knowledge_embeddings_kind_check CHECK (kind IN ('scheme','legal','lawyer'));
