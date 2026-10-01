"""Atomic, duplicate-safe intake. Worker resumes each small part independently."""
import hashlib
import shutil
import time
import uuid
from pathlib import Path
import pymupdf as fitz
from storage import DATA, REMOTE, FILE_BUDGET, StorageError, db, persist_files

MAX_PAGES = 6000
PART_PAGES = 30
# Conservative reservation for aligned pages and eight field crops per student.
# This is a preflight estimate, not a replacement for transactional file limits.
EVIDENCE_BYTES_PER_STUDENT = 3 * 1024 * 1024

def split_ranges(pages):
    if pages < 2 or pages % 2 or pages > MAX_PAGES:
        raise ValueError('Use 2–6000 pages, with exactly two consecutive pages per student. Remove covers and blank separators first.')
    return [(start, min(start + PART_PAGES, pages)) for start in range(0, pages, PART_PAGES)]

def enqueue(source, exam_id, filename):
    source = Path(source)
    with source.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    folders = []
    try:
        with fitz.open(source) as pdf:
            ranges = split_ranges(len(pdf))
            with db() as c:
                # Shared setup/intake mutex works on SQLite and PostgreSQL.
                c.execute('BEGIN IMMEDIATE')
                existing = c.execute('SELECT id FROM bulk_imports WHERE exam_id=? AND digest=?', (exam_id, digest)).fetchone()
                if existing:
                    parts = c.execute('SELECT batch_id,start_page FROM bulk_parts WHERE import_id=? ORDER BY start_page', (existing['id'],)).fetchall()
                    return {'id': existing['id'], 'duplicate': True, 'batches': [dict(p) for p in parts], 'students': len(pdf)//2}
                if REMOTE:
                    used = c.execute('SELECT COALESCE(SUM(size),0) FROM files').fetchone()[0]
                    # Include work already in the queue, not only saved bytes.
                    pending = c.execute("SELECT COALESCE(SUM(total-done),0) FROM batches WHERE status IN ('queued','processing','failed')").fetchone()[0]
                    estimate = source.stat().st_size + (len(pdf)//2 + pending) * EVIDENCE_BYTES_PER_STUDENT
                    if used + estimate > FILE_BUDGET:
                        raise StorageError('This bulk import exceeds available document capacity including queued work and previews. No papers were added. The administrator must provide more document storage or run this import on the local processing installation.')
                import_id = uuid.uuid4().hex
                c.execute('INSERT INTO bulk_imports VALUES(?,?,?,?,?)', (import_id, exam_id, digest, len(pdf), time.time()))
                parts = []
                for start, end in ranges:
                    batch_id = uuid.uuid4().hex
                    folder = DATA/'batches'/batch_id
                    folder.mkdir(parents=True)
                    folders.append(folder)
                    target = folder/'source.pdf'
                    with fitz.open() as part:
                        part.insert_pdf(pdf, from_page=start, to_page=end-1)
                        part.save(target, garbage=3, deflate=True)
                    persist_files(c, [target])
                    name = f'{Path(filename).stem[:90]} · pages {start+1}–{end}'
                    c.execute('INSERT INTO batches VALUES(?,?,?,?,?,0,?,?,?)',
                              (batch_id, exam_id, name, end-start, (end-start)//2, 'queued', '', time.time()))
                    c.execute('INSERT INTO bulk_parts VALUES(?,?,?)', (import_id, batch_id, start))
                    parts.append({'batch_id': batch_id, 'start_page': start})
                return {'id': import_id, 'duplicate': False, 'batches': parts, 'students': len(pdf)//2}
    except Exception:
        # Only folders created by this failed transaction, never existing batches.
        for folder in folders:
            shutil.rmtree(folder, ignore_errors=True)
        raise
