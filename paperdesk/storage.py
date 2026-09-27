"""Durable PostgreSQL records and private MVP file storage; SQLite for local use.

DATABASE_URL must use a direct connection or a session-mode pooler (port 5432).
No credentials or student data belong in the repository.
"""
from contextlib import contextmanager
from pathlib import Path
import hashlib
import os
import re
import sqlite3
import tempfile

ROOT = Path(__file__).parent
DATA = Path(os.environ.get('PAPERDESK_DATA', ROOT / 'data')).resolve()
DATA.mkdir(parents=True, exist_ok=True)
DB = DATA / 'paperdesk.sqlite'
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
REMOTE = bool(DATABASE_URL)
SCHEMA = os.environ.get('PAPERDESK_DB_SCHEMA', 'paperdesk')
if not re.fullmatch(r'paperdesk(?:_test_[a-f0-9]+)?', SCHEMA):
    raise ValueError('Invalid database schema')
FILE_BUDGET = int(os.environ.get('PAPERDESK_FILE_BUDGET_MB', '180')) * 1024 * 1024

class StorageError(RuntimeError):
    pass

class Row(dict):
    def __getitem__(self, key):
        return tuple(self.values())[key] if isinstance(key, int) else super().__getitem__(key)

def row_factory(cursor):
    names = [c.name for c in cursor.description] if cursor.description else []
    return lambda values: Row(zip(names, values))

def pg_connect():
    import psycopg
    # Require encrypted transport; never fall back to a fresh local database.
    return psycopg.connect(DATABASE_URL, sslmode='require', connect_timeout=15,
                           row_factory=row_factory, prepare_threshold=None)

class PgConnection:
    def __init__(self, conn):
        self.conn = conn
    def execute(self, sql, params=()):
        if sql == 'BEGIN IMMEDIATE':
            return self.conn.execute('SELECT pg_advisory_xact_lock(7392101)')
        return self.conn.execute(sql.replace('?', '%s'), params)
    def executescript(self, sql):
        for statement in sql.split(';'):
            if statement.strip():
                self.conn.execute(statement)

@contextmanager
def db():
    if REMOTE:
        with pg_connect() as c:
            c.execute(f'SET search_path TO {SCHEMA}')
            yield PgConnection(c)
    else:
        if os.environ.get('RENDER') == 'true':
            raise StorageError('Configure DATABASE_URL before using PaperDesk on Render. Local storage is temporary.')
        c = sqlite3.connect(DB, timeout=30)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON')
        try:
            with c:
                yield c
        finally:
            c.close()

DDL = '''
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT,email TEXT UNIQUE,password TEXT,salt TEXT);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER,expires REAL);
CREATE TABLE IF NOT EXISTS exams(id TEXT PRIMARY KEY,name TEXT,class_name TEXT,config TEXT,locked INTEGER DEFAULT 0,created REAL);
CREATE TABLE IF NOT EXISTS batches(id TEXT PRIMARY KEY,exam_id TEXT,name TEXT,pages INTEGER,total INTEGER,done INTEGER DEFAULT 0,status TEXT,error TEXT,created REAL);
CREATE TABLE IF NOT EXISTS papers(id TEXT PRIMARY KEY,batch_id TEXT,idx INTEGER,data TEXT,status TEXT,version INTEGER DEFAULT 1,UNIQUE(batch_id,idx));
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,paper_id TEXT,user_id INTEGER,at REAL,before_data TEXT,after_data TEXT);
'''

def initialize():
    if REMOTE:
        with pg_connect() as c:
            c.execute('SELECT pg_advisory_xact_lock(7392100)')
            c.execute(f'CREATE SCHEMA IF NOT EXISTS {SCHEMA}')
            c.execute(f'REVOKE ALL ON SCHEMA {SCHEMA} FROM PUBLIC')
            # Supabase browser/API roles must never read password hashes or scans.
            for role in ('anon', 'authenticated'):
                if c.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', (role,)).fetchone():
                    c.execute(f'REVOKE ALL ON SCHEMA {SCHEMA} FROM {role}')
            c.execute(f'SET search_path TO {SCHEMA}')
            ddl = DDL.replace('id INTEGER PRIMARY KEY', 'id BIGSERIAL PRIMARY KEY').replace(' REAL', ' DOUBLE PRECISION')
            PgConnection(c).executescript(ddl)
            c.execute('CREATE TABLE IF NOT EXISTS files(key TEXT PRIMARY KEY, digest TEXT NOT NULL, size BIGINT NOT NULL, content BYTEA NOT NULL)')
            c.execute(f'REVOKE ALL ON ALL TABLES IN SCHEMA {SCHEMA} FROM PUBLIC')
            for role in ('anon', 'authenticated'):
                if c.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', (role,)).fetchone():
                    c.execute(f'REVOKE ALL ON ALL TABLES IN SCHEMA {SCHEMA} FROM {role}')
    else:
        with db() as c:
            c.executescript('PRAGMA journal_mode=WAL;' + DDL)

def file_key(path):
    key = Path(path).resolve().relative_to(DATA).as_posix()
    if not key.startswith(('exams/', 'batches/')):
        raise StorageError('Invalid document path')
    return key

def persist_files(c, paths):
    """Save evidence in the SAME transaction as the record that refers to it."""
    if not REMOTE:
        return
    c.execute('SELECT pg_advisory_xact_lock(7392102)')
    used = c.execute('SELECT COALESCE(SUM(size),0) FROM files').fetchone()[0]
    for path in paths:
        path = Path(path)
        key = file_key(path)
        data = path.read_bytes()
        old = c.execute('SELECT size FROM files WHERE key=?', (key,)).fetchone()
        used += len(data) - (old[0] if old else 0)
        if used > FILE_BUDGET:
            raise StorageError('Paper storage is full. No new data was saved. Contact the administrator to archive batches or increase storage.')
        c.execute('INSERT INTO files(key,digest,size,content) VALUES(?,?,?,?) ON CONFLICT(key) DO UPDATE SET digest=excluded.digest,size=excluded.size,content=excluded.content',
                  (key, hashlib.sha256(data).hexdigest(), len(data), data))

def available(path):
    if not REMOTE:
        return Path(path).exists()
    with db() as c:
        return bool(c.execute('SELECT 1 FROM files WHERE key=?', (file_key(path),)).fetchone())

def materialize(path):
    """Local files are disposable caches. Durable bytes remain in PostgreSQL."""
    path = Path(path)
    if not REMOTE:
        return path
    with db() as c:
        info = c.execute('SELECT digest FROM files WHERE key=?', (file_key(path),)).fetchone()
        if not info:
            raise FileNotFoundError('Stored document not found')
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == info['digest']:
            return path
        row = c.execute('SELECT content,digest FROM files WHERE key=?', (file_key(path),)).fetchone()
    data = bytes(row['content'])
    if hashlib.sha256(data).hexdigest() != row['digest']:
        raise StorageError('Stored document integrity check failed')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.restore-')
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)
    return path

@contextmanager
def worker_leadership(stop):
    """One active queue reader, including during overlapping Render deploys."""
    if not REMOTE:
        yield lambda: None
        return
    with pg_connect() as c:
        c.autocommit = True
        while not stop.is_set():
            if c.execute('SELECT pg_try_advisory_lock(7392103)').fetchone()[0]:
                try:
                    yield lambda: c.execute('SELECT 1')
                finally:
                    c.execute('SELECT pg_advisory_unlock(7392103)')
                return
            stop.wait(1)
        yield None
