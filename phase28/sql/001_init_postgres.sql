-- Production-style multi-task storage. Apply through approved one-shot migration process.
CREATE TABLE IF NOT EXISTS sources (
  source_id varchar(128) PRIMARY KEY,
  tenant_id varchar(128) NOT NULL,
  domain varchar(128) NOT NULL,
  record_id varchar(128),
  content text NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_source_scope ON sources (tenant_id, domain, record_id);
CREATE TABLE IF NOT EXISTS audit (
  id varchar(64) PRIMARY KEY, ts timestamptz NOT NULL, actor varchar(128) NOT NULL,
  tenant_id varchar(128) NOT NULL, domain varchar(128) NOT NULL,
  outcome varchar(32) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit(ts);
CREATE TABLE IF NOT EXISTS model_attempts (
  id varchar(64) PRIMARY KEY, tenant_id varchar(128) NOT NULL,
  day date NOT NULL, ts timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_model_tenant_day ON model_attempts(tenant_id, day);
