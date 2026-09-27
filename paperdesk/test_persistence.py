"""Opt-in PostgreSQL restart check. Requires an isolated paperdesk_test_* schema."""
import os, tempfile, unittest, json, hashlib
from pathlib import Path
if not os.environ.get('DATABASE_URL') or not os.environ.get('PAPERDESK_DB_SCHEMA','').startswith('paperdesk_test_'):
    raise RuntimeError('Use an isolated PostgreSQL test schema')
cache=tempfile.TemporaryDirectory();os.environ['PAPERDESK_DATA']=cache.name
import storage
from storage import db,initialize,persist_files,materialize,available,StorageError

class Persistence(unittest.TestCase):
    def test_empty_cache_restart_and_rollback(self):
        initialize()
        source=storage.DATA/'batches'/'persistence-fixture'/'source.pdf'
        source.parent.mkdir(parents=True);payload=b'%PDF-synthetic-storage-fixture';source.write_bytes(payload)
        with db() as c:
            c.execute("INSERT INTO users(name,email,password,salt) VALUES(?,?,?,?)",('Synthetic persistence user','persistence@example.test','synthetic-hash','synthetic-salt'))
            c.execute('INSERT INTO exams VALUES(?,?,?,?,?,?)',('restart-fixture','Restart fixture','10','{}',0,1.0))
            persist_files(c,[source])
        source.unlink()
        initialize()
        with db() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM users').fetchone()[0],1)
        self.assertTrue(available(source))
        self.assertEqual(materialize(source).read_bytes(),payload)
        source.write_bytes(b'stale cache')
        self.assertEqual(materialize(source).read_bytes(),payload)
        before=storage.FILE_BUDGET;storage.FILE_BUDGET=0
        try:
            with self.assertRaises(StorageError):
                with db() as c:
                    c.execute("UPDATE exams SET name='should rollback' WHERE id='restart-fixture'")
                    persist_files(c,[source])
        finally:storage.FILE_BUDGET=before
        with db() as c:
            self.assertEqual(c.execute("SELECT name FROM exams WHERE id='restart-fixture'").fetchone()[0],'Restart fixture')
            for role in ['anon','authenticated']:
                self.assertFalse(c.execute('SELECT has_schema_privilege(?, ?, ?)',(role,storage.SCHEMA,'USAGE')).fetchone()[0])
        with self.assertRaises(StorageError):storage.file_key(storage.DATA/'not-a-document')

if __name__=='__main__':unittest.main()
