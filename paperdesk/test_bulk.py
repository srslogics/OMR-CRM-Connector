"""Bulk intake uses generated PDFs only; no private records or server credentials."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pymupdf as fitz

if os.environ.get('DATABASE_URL'):
    raise RuntimeError('Run this fixture with a local temporary database.')
temporary = tempfile.TemporaryDirectory()
os.environ['PAPERDESK_DATA'] = temporary.name
import bulk
from storage import initialize, db, DATA, StorageError

class BulkIntake(unittest.TestCase):
    def setUp(self):
        initialize()
    def pdf(self, name, pages):
        path = Path(temporary.name)/name
        with fitz.open() as pdf:
            for i in range(pages):
                page = pdf.new_page(width=100, height=100)
                page.insert_text((10,50), str(i+1))
            pdf.save(path)
        return path
    def test_full_2610_student_pairing_boundaries(self):
        ranges = bulk.split_ranges(5220)
        self.assertEqual(len(ranges),174)
        self.assertEqual(ranges[0],(0,30))
        self.assertEqual(ranges[-1],(5190,5220))
        self.assertTrue(all(a%2==0 and b%2==0 and b-a<=30 for a,b in ranges))
    def test_split_keeps_page_order_and_retry_is_idempotent(self):
        source=self.pdf('61-students.pdf',122)
        result=bulk.enqueue(source,'split-test','combined.pdf')
        self.assertEqual(len(result['batches']),5)
        self.assertEqual(result['students'],61)
        seen=[]
        for p in result['batches']:
            with fitz.open(DATA/'batches'/p['batch_id']/'source.pdf') as pdf:
                seen.extend(int(page.get_text().strip()) for page in pdf)
        self.assertEqual(seen,list(range(1,123)))
        retry=bulk.enqueue(source,'split-test','renamed.pdf')
        self.assertTrue(retry['duplicate'])
        self.assertEqual(result['batches'],retry['batches'])
    def test_failure_rolls_back_whole_import_and_removes_only_new_files(self):
        source=self.pdf('rollback.pdf',32)
        with db() as c:before=c.execute('SELECT count(*) FROM batches').fetchone()[0]
        folders=set((DATA/'batches').iterdir()) if (DATA/'batches').exists() else set()
        with patch.object(bulk,'persist_files',side_effect=[None,StorageError('Full')]):
            with self.assertRaises(StorageError):bulk.enqueue(source,'rollback-test','failed.pdf')
        with db() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM batches').fetchone()[0],before)
            self.assertEqual(c.execute('SELECT count(*) FROM bulk_imports WHERE exam_id=?',('rollback-test',)).fetchone()[0],0)
        self.assertEqual(set((DATA/'batches').iterdir()),folders)
    def test_odd_or_oversized_pdf_never_creates_batches(self):
        for pages in (0,1,31,6002):
            with self.assertRaises(ValueError):bulk.split_ranges(pages)
    def test_remote_capacity_failure_is_before_any_split(self):
        source=self.pdf('capacity.pdf',2)
        with db() as c:
            c.execute('CREATE TABLE IF NOT EXISTS files(size INTEGER)')
        with patch.object(bulk,'REMOTE',True),patch.object(bulk,'FILE_BUDGET',1):
            with self.assertRaises(StorageError):bulk.enqueue(source,'capacity-test','capacity.pdf')
        with db() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM bulk_imports WHERE exam_id=?',('capacity-test',)).fetchone()[0],0)

if __name__=='__main__':unittest.main()
