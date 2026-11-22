CREATE TABLE organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    workspace_path TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE agent_profiles (
    id TEXT NOT NULL,
    version TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    definition TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, id, version)
);

CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    agent_profile_id TEXT NOT NULL,
    agent_profile_version TEXT NOT NULL,
    prompt TEXT NOT NULL,
    status TEXT NOT NULL,
    idempotency_key TEXT,
    workspace_path TEXT NOT NULL,
    result TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX uq_tasks_tenant_idempotency
    ON tasks (tenant_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE task_events (
    tenant_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    payload TEXT NOT NULL,
    correlation_id TEXT,
    PRIMARY KEY (task_id, sequence)
);

CREATE INDEX ix_task_events_tenant_task ON task_events (tenant_id, task_id, sequence);

CREATE TABLE usage_events (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    occurred_at TEXT NOT NULL
);
