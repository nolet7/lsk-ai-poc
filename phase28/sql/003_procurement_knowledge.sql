-- Synthetic approved supplier documents, versioned with role ACLs.
CREATE TABLE IF NOT EXISTS procurement_knowledge (
  tenant_id varchar(128) NOT NULL,
  source_id varchar(128) NOT NULL,
  po_id varchar(128) NOT NULL,
  doc_type varchar(20) NOT NULL CHECK (doc_type IN ('contract','certificate','policy')),
  source_version integer NOT NULL CHECK (source_version > 0),
  source_uri varchar(512) NOT NULL,
  classification varchar(32) NOT NULL CHECK (classification='synthetic'),
  authorized_roles text[] NOT NULL CHECK (array_length(authorized_roles,1) >= 1),
  content text NOT NULL CHECK (length(content) BETWEEN 1 AND 5000),
  content_sha256 char(64) NOT NULL,
  approved_at timestamptz NOT NULL,
  retired_at timestamptz,
  PRIMARY KEY (tenant_id,source_id),
  FOREIGN KEY (tenant_id,po_id) REFERENCES procurement_pos(tenant_id,po_id)
);
CREATE INDEX IF NOT EXISTS idx_proc_docs_scope
  ON procurement_knowledge(tenant_id,po_id);
CREATE INDEX IF NOT EXISTS idx_proc_docs_roles
  ON procurement_knowledge USING gin(authorized_roles);
CREATE INDEX IF NOT EXISTS idx_proc_docs_lexical
  ON procurement_knowledge USING gin(to_tsvector('english',content));
