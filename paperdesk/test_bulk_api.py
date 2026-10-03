"""Authenticated bulk intake and interruption recovery, with synthetic scans."""
import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
if os.environ.get('DATABASE_URL'):
    raise RuntimeError('Use a local temporary database for this test.')
temporary = tempfile.TemporaryDirectory()
os.environ['PAPERDESK_DATA'] = temporary.name
from fastapi.testclient import TestClient
import app as service
from sample import create_pdf

class BulkAPI(unittest.TestCase):
    def test_authenticated_intake_and_resume_preserve_completed_record(self):
        with patch.object(service,'work_loop'), TestClient(service.app) as client:
            self.assertEqual(client.post('/api/bulk-imports',data={'exam_id':'x','pairing_confirmed':'true'},files={'file':('x.pdf',b'bad','application/pdf')}).status_code,401)
            self.assertEqual(client.get('/api/operations').status_code,401)
            client.post('/api/setup',json={'name':'Internal QA','email':'qa@example.test','password':'synthetic-password'})
            eid=client.post('/api/exams',json={'name':'Bulk QA','class_name':'10'}).json()['id']
            blank=Path(temporary.name)/'blank.pdf';config=create_pdf(blank)
            client.post(f'/api/exams/{eid}/template',files={'file':('blank.pdf',blank.read_bytes(),'application/pdf')})
            client.put(f'/api/exams/{eid}',json=config)
            client.post(f'/api/exams/{eid}/lock')
            scans=Path(temporary.name)/'scans.pdf';create_pdf(scans,['Synthetic One','Synthetic Two','Synthetic Three'])
            files={'file':('scans.pdf',scans.read_bytes(),'application/pdf')}
            self.assertEqual(client.post('/api/bulk-imports',data={'exam_id':eid},files=files).status_code,400)
            r=client.post('/api/bulk-imports',data={'exam_id':eid,'pairing_confirmed':'true'},files=files)
            self.assertEqual(r.status_code,200,r.text)
            bid=r.json()['batches'][0]['batch_id'];batch=service.require_row('batches',bid)
            original=service.extract_details
            def interrupt_after_first(*args,**kwargs):
                readings=original(*args,**kwargs)
                service.stop.set()
                return readings
            with patch.object(service,'extract_details',side_effect=interrupt_after_first):
                service.process_batch(batch)
            with service.read_db() as c:
                before=[dict(p) for p in c.execute('SELECT * FROM papers WHERE batch_id=?',(bid,)).fetchall()]
            self.assertEqual(len(before),1)
            service.stop.clear()
            service.process_batch(service.require_row('batches',bid))
            with service.read_db() as c:
                after=[dict(p) for p in c.execute('SELECT * FROM papers WHERE batch_id=? ORDER BY idx',(bid,)).fetchall()]
            self.assertEqual(len(after),3)
            self.assertEqual(before[0],after[0])
            self.assertEqual(service.require_row('batches',bid)['status'],'ready')
            queue=client.get('/api/operations?limit=2').json()
            self.assertEqual(queue['counts']['awaiting_team'],3)
            detail=client.get('/api/papers/'+queue['items'][0]['id']).json()
            self.assertEqual(detail['source_pages'],[1,2])
            self.assertEqual(detail['source_student'],1)
            self.assertEqual(len(queue['items']),2)
            self.assertEqual(queue['next_offset'],2)
            next_page=client.get('/api/operations?limit=2&offset=2').json()
            self.assertEqual(len(next_page['items']),1)
            self.assertIsNone(next_page['next_offset'])
            self.assertFalse(queue['capacity']['remote'])
            self.assertEqual(client.get('/api/operations?limit=1000').status_code,422)
            self.assertEqual(client.get('/api/operations?offset=-1').status_code,422)

            duplicate=client.post('/api/bulk-imports',data={'exam_id':eid,'pairing_confirmed':'true'},files=files).json()
            self.assertTrue(duplicate['duplicate'])
            self.assertEqual(duplicate['batches'][0]['batch_id'],bid)

if __name__=='__main__':unittest.main()
