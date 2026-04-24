-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Projects
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- API Keys
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    key_hash TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    scopes TEXT[] NOT NULL DEFAULT '{"ingest","read","write"}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);

-- Sessions
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    first_seen TIMESTAMPTZ NOT NULL,
    last_seen TIMESTAMPTZ NOT NULL,
    trace_count INT NOT NULL DEFAULT 0,
    span_count INT NOT NULL DEFAULT 0,
    total_cost_usd NUMERIC(10,4) DEFAULT 0,
    total_tokens_in BIGINT DEFAULT 0,
    total_tokens_out BIGINT DEFAULT 0,
    has_error BOOLEAN DEFAULT false,
    summary TEXT,
    summary_model TEXT,
    user_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_sessions_project ON sessions(project_id);
CREATE INDEX idx_sessions_last_seen ON sessions(last_seen DESC);
CREATE INDEX idx_sessions_has_error ON sessions(has_error) WHERE has_error = true;

-- Annotations
CREATE TABLE annotations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    target_type TEXT NOT NULL CHECK (target_type IN ('span', 'trace', 'session')),
    target_id TEXT NOT NULL,
    author_id UUID,
    author_kind TEXT NOT NULL CHECK (author_kind IN ('human', 'llm_judge')),
    verdict SMALLINT CHECK (verdict IN (-1, 0, 1)),
    failure_modes TEXT[] DEFAULT '{}',
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_annotations_target ON annotations(target_type, target_id);

-- Eval Suites
CREATE TABLE eval_suites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Rubrics
CREATE TABLE rubrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    grader_type TEXT NOT NULL,
    config JSONB NOT NULL DEFAULT '{}',
    source_annotation_ids UUID[] DEFAULT '{}',
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Evals
CREATE TABLE evals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    suite_id UUID NOT NULL REFERENCES eval_suites(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    input_fixture JSONB NOT NULL,
    rubric_id UUID NOT NULL REFERENCES rubrics(id),
    expected JSONB,
    origin_trace_id TEXT,
    version INT NOT NULL DEFAULT 1,
    enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_evals_suite ON evals(suite_id);

-- Runs
CREATE TABLE runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    suite_id UUID NOT NULL REFERENCES eval_suites(id) ON DELETE CASCADE,
    agent_version TEXT,
    triggered_by TEXT CHECK (triggered_by IN ('ci', 'manual', 'scheduled')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    passed INT DEFAULT 0,
    failed INT DEFAULT 0,
    regressed INT DEFAULT 0,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    report JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_runs_suite ON runs(suite_id);

-- Failure embeddings for clustering
CREATE TABLE failure_embeddings (
    annotation_id UUID PRIMARY KEY REFERENCES annotations(id) ON DELETE CASCADE,
    embedding vector(1024),
    model TEXT NOT NULL
);
CREATE INDEX idx_failure_embeddings_vector ON failure_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
