-- Synthetic commercial domain; no actual ERP writes.
CREATE TABLE IF NOT EXISTS procurement_pos (
  tenant_id varchar(128) NOT NULL,
  po_id varchar(128) NOT NULL,
  supplier_id varchar(128) NOT NULL,
  quantity numeric(18,4) NOT NULL CHECK (quantity > 0),
  contract_unit_price numeric(18,4) NOT NULL CHECK (contract_unit_price >= 0),
  currency varchar(8) NOT NULL,
  PRIMARY KEY (tenant_id,po_id)
);
CREATE TABLE IF NOT EXISTS procurement_invoices (
  tenant_id varchar(128) NOT NULL,
  invoice_id varchar(128) NOT NULL,
  po_id varchar(128) NOT NULL,
  invoice_total numeric(18,4) NOT NULL CHECK (invoice_total >= 0),
  PRIMARY KEY (tenant_id,invoice_id),
  FOREIGN KEY (tenant_id,po_id) REFERENCES procurement_pos(tenant_id,po_id)
);
CREATE INDEX IF NOT EXISTS idx_proc_invoice_po ON procurement_invoices (tenant_id,po_id);
CREATE TABLE IF NOT EXISTS procurement_certificates (
  tenant_id varchar(128) NOT NULL,
  supplier_id varchar(128) NOT NULL,
  certificate_id varchar(128) NOT NULL,
  expires_on date NOT NULL,
  PRIMARY KEY (tenant_id,supplier_id,certificate_id)
);
CREATE TABLE IF NOT EXISTS procurement_exceptions (
  id varchar(64) PRIMARY KEY,
  tenant_id varchar(128) NOT NULL,
  po_id varchar(128) NOT NULL,
  requester varchar(128) NOT NULL,
  idempotency_key varchar(128) NOT NULL,
  fingerprint text NOT NULL,
  status varchar(16) NOT NULL CHECK (status IN ('pending','approved','rejected')),
  created_at timestamptz NOT NULL,
  reviewer varchar(128),
  reviewed_at timestamptz,
  UNIQUE (tenant_id,requester,idempotency_key),
  FOREIGN KEY (tenant_id,po_id) REFERENCES procurement_pos(tenant_id,po_id)
);
CREATE INDEX IF NOT EXISTS idx_proc_exceptions_tenant ON procurement_exceptions(tenant_id,status);
