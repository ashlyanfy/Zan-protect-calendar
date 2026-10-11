CREATE TABLE IF NOT EXISTS scheme_cards (
    id text PRIMARY KEY,
    category text NOT NULL,
    title_ru text NOT NULL,
    title_kk text NOT NULL,
    card jsonb NOT NULL,
    status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','reviewed','retired')),
    reviewed_by text,
    reviewed_at timestamptz,
    search_text text NOT NULL,
    search_vector tsvector GENERATED ALWAYS AS (to_tsvector('simple', search_text)) STORED,
    CHECK (status <> 'reviewed' OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS scheme_search_idx ON scheme_cards USING gin(search_vector);
CREATE TABLE IF NOT EXISTS legal_sources (
    id text PRIMARY KEY,
    title text NOT NULL,
    url text NOT NULL,
    jurisdiction text NOT NULL DEFAULT 'KZ' CHECK (jurisdiction = 'KZ'),
    language text NOT NULL CHECK(language IN ('ru','kk')),
    excerpt text NOT NULL,
    effective_from date,
    effective_to date,
    checked_on date NOT NULL,
    review_due date NOT NULL,
    approved_by text,
    approved boolean NOT NULL DEFAULT false,
    search_vector tsvector GENERATED ALWAYS AS (to_tsvector('simple', title || ' ' || excerpt)) STORED,
    CHECK (NOT approved OR approved_by IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS legal_search_idx ON legal_sources USING gin(search_vector);
-- Intentionally no Telegram updates, chat messages, uploads or personal profiles.
