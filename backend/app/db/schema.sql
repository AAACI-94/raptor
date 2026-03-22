-- RAPTOR v1.0 Database Schema
-- SQLite with WAL mode, JSON1 extension for structured queries

-- Projects: top-level authoring container
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    topic_description TEXT,
    author_context TEXT,
    venue_profile_id TEXT REFERENCES venue_profiles(id),
    status TEXT NOT NULL DEFAULT 'TOPIC_SELECTED',
    nda_config TEXT,  -- JSON: sensitivity_level, mode, blocked_terms, generalization_rules
    revision_cycles INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Artifact Store (immutable: every version preserved)
CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    artifact_type TEXT NOT NULL,
    source_agent TEXT NOT NULL,
    target_agent TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'draft',
    envelope TEXT NOT NULL,  -- Full artifact envelope as JSON
    created_at TEXT NOT NULL,
    UNIQUE(project_id, artifact_type, source_agent, version)
);

CREATE INDEX IF NOT EXISTS idx_artifacts_project ON artifacts(project_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(artifact_type);
CREATE INDEX IF NOT EXISTS idx_artifacts_status ON artifacts(status);

-- Venue Profiles: quality standards per publication type
CREATE TABLE IF NOT EXISTS venue_profiles (
    id TEXT PRIMARY KEY,
    venue_type TEXT NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT,
    profile_data TEXT NOT NULL,  -- Full venue profile as JSON
    is_custom BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Observatory: Decision Logs
CREATE TABLE IF NOT EXISTS decision_logs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    artifact_id TEXT REFERENCES artifacts(id),
    agent TEXT NOT NULL,
    decision TEXT NOT NULL,
    rationale TEXT,
    alternatives_considered TEXT,  -- JSON array
    confidence REAL,
    trace_id TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_decisions_project ON decision_logs(project_id);
CREATE INDEX IF NOT EXISTS idx_decisions_agent ON decision_logs(agent);

-- Observatory: Quality Scores
CREATE TABLE IF NOT EXISTS quality_scores (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    artifact_id TEXT NOT NULL REFERENCES artifacts(id),
    section_name TEXT,
    dimension TEXT NOT NULL,
    score REAL NOT NULL,
    reviewer_agent TEXT NOT NULL,
    feedback TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_quality_project ON quality_scores(project_id);
CREATE INDEX IF NOT EXISTS idx_quality_dimension ON quality_scores(dimension);

-- Observatory: Token/Cost Tracking
CREATE TABLE IF NOT EXISTS token_usage (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    artifact_id TEXT REFERENCES artifacts(id),
    agent TEXT NOT NULL,
    operation TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_write_tokens INTEGER DEFAULT 0,
    estimated_cost_usd REAL NOT NULL,
    trace_id TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tokens_project ON token_usage(project_id);
CREATE INDEX IF NOT EXISTS idx_tokens_agent ON token_usage(agent);

-- Observatory: Author Feedback
CREATE TABLE IF NOT EXISTS author_feedback (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    artifact_id TEXT NOT NULL REFERENCES artifacts(id),
    dimension TEXT NOT NULL,
    author_rating REAL NOT NULL,
    system_rating REAL NOT NULL,
    delta REAL NOT NULL,
    feedback_text TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_feedback_project ON author_feedback(project_id);

-- Improvement Store: Rubric Weight Adjustments
CREATE TABLE IF NOT EXISTS rubric_adjustments (
    id TEXT PRIMARY KEY,
    venue_profile_id TEXT NOT NULL REFERENCES venue_profiles(id),
    dimension TEXT NOT NULL,
    old_weight REAL NOT NULL,
    new_weight REAL NOT NULL,
    trigger_type TEXT NOT NULL,  -- 'author_rating', 'manual', 'drift_detection'
    trigger_feedback_ids TEXT,  -- JSON array of author_feedback IDs
    rationale TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Improvement Store: Baseline Snapshots (for rollback)
CREATE TABLE IF NOT EXISTS rubric_snapshots (
    id TEXT PRIMARY KEY,
    venue_profile_id TEXT NOT NULL REFERENCES venue_profiles(id),
    rubric_data TEXT NOT NULL,  -- Full rubric as JSON
    snapshot_reason TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Research Corpus (per-project knowledge base metadata)
CREATE TABLE IF NOT EXISTS research_sources (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    source_type TEXT NOT NULL,
    title TEXT NOT NULL,
    authors TEXT,  -- JSON array
    publication TEXT,
    year INTEGER,
    url TEXT,
    doi TEXT,
    relevance_score REAL,
    authority_score REAL,
    content_summary TEXT,
    content_hash TEXT,  -- SHA-256 for dedup
    embedding_id TEXT,  -- Reference to vector store entry
    retrieved_date TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sources_project ON research_sources(project_id);

-- Audit Log
CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),
    action TEXT NOT NULL,
    agent TEXT,
    detail TEXT,
    trace_id TEXT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_audit_project ON audit_log(project_id);
