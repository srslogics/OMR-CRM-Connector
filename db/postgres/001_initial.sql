CREATE SCHEMA IF NOT EXISTS srs_records;
REVOKE ALL ON SCHEMA srs_records FROM PUBLIC;
CREATE TABLE IF NOT EXISTS srs_records.ownership(id integer PRIMARY KEY CHECK(id=1),user_id text NOT NULL,email text NOT NULL);
CREATE TABLE IF NOT EXISTS srs_records.members(email text PRIMARY KEY,name text NOT NULL,user_id text,active integer NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS srs_records.records(id text PRIMARY KEY,name text NOT NULL,school text NOT NULL,father_phone text NOT NULL,mother_phone text NOT NULL,class_name text NOT NULL,submitter_id text NOT NULL,submitter_email text NOT NULL,status text NOT NULL DEFAULT 'New',created_at text NOT NULL,updated_at text NOT NULL);
CREATE INDEX IF NOT EXISTS idx_records_submitter ON srs_records.records(submitter_id);
CREATE INDEX IF NOT EXISTS idx_records_created ON srs_records.records(created_at);
CREATE TABLE IF NOT EXISTS srs_records.auth_accounts(id text PRIMARY KEY,phone text UNIQUE NOT NULL,name text NOT NULL,role text NOT NULL CHECK(role IN ('owner','intern')),password_hash text NOT NULL,active integer NOT NULL DEFAULT 1);
CREATE UNIQUE INDEX IF NOT EXISTS single_owner ON srs_records.auth_accounts(role) WHERE role='owner';
CREATE TABLE IF NOT EXISTS srs_records.auth_sessions(token_hash text PRIMARY KEY,account_id text NOT NULL REFERENCES srs_records.auth_accounts(id),expires_at bigint NOT NULL);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_account ON srs_records.auth_sessions(account_id);
CREATE TABLE IF NOT EXISTS srs_records.auth_attempts(key text PRIMARY KEY,count integer NOT NULL,reset_at bigint NOT NULL);
REVOKE ALL ON ALL TABLES IN SCHEMA srs_records FROM PUBLIC;

ALTER TABLE srs_records.auth_sessions ADD COLUMN IF NOT EXISTS last_active_at bigint NOT NULL DEFAULT (extract(epoch FROM clock_timestamp())*1000)::bigint;
DELETE FROM srs_records.auth_sessions WHERE token_hash IN (SELECT token_hash FROM (SELECT token_hash,row_number() OVER (PARTITION BY account_id ORDER BY expires_at DESC,token_hash) AS rn FROM srs_records.auth_sessions) ranked WHERE rn>1);
CREATE UNIQUE INDEX IF NOT EXISTS single_session_per_account ON srs_records.auth_sessions(account_id);
CREATE TABLE IF NOT EXISTS srs_records.activity_log(id bigserial PRIMARY KEY,actor_id text,actor_name text NOT NULL,event text NOT NULL,created_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS activity_log_created ON srs_records.activity_log(created_at DESC);
REVOKE ALL ON srs_records.activity_log FROM PUBLIC;

ALTER TABLE srs_records.records ADD COLUMN IF NOT EXISTS marks numeric;
