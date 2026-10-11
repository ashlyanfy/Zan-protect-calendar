CREATE TABLE IF NOT EXISTS private_sessions (
    id text PRIMARY KEY,
    payload bytea NOT NULL,
    expires_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS session_expiry ON private_sessions(expires_at);
CREATE TABLE IF NOT EXISTS request_quotas (
    id text NOT NULL,
    day date NOT NULL,
    requests integer NOT NULL DEFAULT 0,
    PRIMARY KEY(id,day)
);
CREATE TABLE IF NOT EXISTS bot_jobs (
    update_id bigint PRIMARY KEY,
    session_id text NOT NULL,
    payload bytea,
    status text NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','running','done','failed','cancelled')),
    attempts integer NOT NULL DEFAULT 0,
    lease_until timestamptz,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS jobs_ready ON bot_jobs(status,created_at);
CREATE INDEX IF NOT EXISTS jobs_session ON bot_jobs(session_id);
CREATE TABLE IF NOT EXISTS knowledge_embeddings (
    kind text NOT NULL CHECK(kind IN ('scheme','legal')),
    item_id text NOT NULL,
    model text NOT NULL,
    dimensions integer NOT NULL,
    content_hash text NOT NULL,
    embedding real[] NOT NULL,
    PRIMARY KEY(kind,item_id),
    CHECK(array_length(embedding,1)=dimensions)
);
CREATE TABLE IF NOT EXISTS editorial_audit (
    id bigserial PRIMARY KEY,
    kind text NOT NULL,
    item_id text NOT NULL,
    action text NOT NULL,
    actor text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
