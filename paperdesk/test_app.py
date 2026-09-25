"""Integration checks with generated scans. Never uses real student records."""
import os,tempfile,time,unittest,io,json
from pathlib import Path
TEST_DIR=tempfile.TemporaryDirectory();os.environ['PAPERDESK_DATA']=TEST_DIR.name
from fastapi.testclient import TestClient
from app import app,db,DATA,process_batch,require_row
from sample import create_pdf,KEY
from processor import score,validate_config,raster,align,detect_question
import pymupdf as fitz
import cv2

class Integration(unittest.TestCase):
 def test_public_monitor_head(self):
  with TestClient(app) as client:
   head=client.head('/')
   page=client.get('/')
   self.assertEqual(head.status_code,200)
   self.assertEqual(head.content,b'')
   self.assertEqual(head.headers['content-type'],page.headers['content-type'])
   self.assertEqual(head.headers['content-length'],page.headers['content-length'])
   self.assertEqual(client.head('/').headers['x-content-type-options'],'nosniff')
   self.assertEqual(client.get('/api/dashboard').status_code,401)
 def test_workflow(self):
  with TestClient(app) as client:
   self.assertEqual(client.get('/api/dashboard').status_code,401)
   self.assertEqual(client.post('/api/setup',json={'name':'Test Operator','email':'operator@example.test','password':'long-test-password'}).status_code,200)
   self.assertEqual(client.post('/api/setup',json={'name':'X','email':'x@y.test','password':'another-password'}).status_code,409)
   self.assertEqual(client.post('/api/exams',headers={'Origin':'https://attacker.example'},json={}).status_code,403)
   eid=client.post('/api/exams',json={'name':'Integration fixture','class_name':'9'}).json()['id']
   fixture=Path(TEST_DIR.name)/'blank.pdf';config=create_pdf(fixture)
   self.assertEqual(client.post(f'/api/exams/{eid}/template',files={'file':('blank.pdf',fixture.read_bytes(),'application/pdf')}).status_code,200)
   self.assertEqual(client.post(f'/api/exams/{eid}/lock').status_code,400)
   self.assertEqual(client.put(f'/api/exams/{eid}',json=config).status_code,200)
   self.assertEqual(client.post(f'/api/exams/{eid}/lock').status_code,200)
   self.assertEqual(client.put(f'/api/exams/{eid}',json=config).status_code,409)
   student=Path(TEST_DIR.name)/'students.pdf';create_pdf(student,['First Test','Second Test','Third Test'])
   # A single-page upload is rejected to avoid shifting student pairing.
   with fitz.open(student) as d:
    odd=fitz.open();odd.insert_pdf(d,from_page=0,to_page=0);odd_bytes=odd.tobytes();odd.close()
   self.assertEqual(client.post('/api/batches',data={'exam_id':eid},files={'file':('odd.pdf',odd_bytes,'application/pdf')}).status_code,400)
   r=client.post('/api/batches',data={'exam_id':eid},files={'file':('students.pdf',student.read_bytes(),'application/pdf')});self.assertEqual(r.status_code,200,r.text);bid=r.json()['id']
   deadline=time.time()+90
   while time.time()<deadline:
    b=client.get(f'/api/batches/{bid}').json()
    if b['status'] in ('ready','failed'):break
    time.sleep(.2)
   self.assertEqual(b['status'],'ready',b)
   self.assertEqual(len(b['papers']),3)
   first,second,third=b['papers'];print('Detected scores:',[(p['data']['score']) for p in b['papers']])
   self.assertEqual(first['data']['answers'],KEY)
   self.assertEqual(first['data']['fields']['name'].casefold(),'first test')
   self.assertEqual(client.get(f'/api/batches/{bid}/source').status_code,200)
   self.assertEqual(first['data']['score']['total'],100)
   self.assertEqual(second['data']['score']['total'],76)
   self.assertEqual(third['data']['answers'][4],'-')
   self.assertEqual(third['data']['answers'][19],'?')
   self.assertEqual(client.get(f'/api/batches/{bid}/export/csv').status_code,400)
   review={'answers':first['data']['answers'],'fields':{'name':'First Test'},'approve':True,'version':1,'pairing_verified':False}
   self.assertEqual(client.put('/api/papers/'+first['id'],json=review).status_code,400)
   review['pairing_verified']=True
   self.assertEqual(client.put('/api/papers/'+first['id'],json=review).status_code,200)
   self.assertEqual(client.put('/api/papers/'+first['id'],json=review).status_code,409)
   self.assertEqual(client.get(f'/api/batches/{bid}/export/xlsx').status_code,200)
   csv=client.get(f'/api/batches/{bid}/export/csv').text
   self.assertIn('First Test',csv);self.assertNotIn('Second Test',csv)
   self.assertTrue(client.get('/api/papers/'+first['id']+'/marksheet').content.startswith(b'%PDF'))
   with db() as c:self.assertEqual(c.execute('SELECT count(*) FROM audit').fetchone()[0],1)
   # Exercise both sides of the MVP batch limit through the upload API.
   oversized=Path(TEST_DIR.name)/'sixteen.pdf';create_pdf(oversized,[f'Limit Test {i}' for i in range(16)])
   rejected=client.post('/api/batches',data={'exam_id':eid},files={'file':('sixteen.pdf',oversized.read_bytes(),'application/pdf')})
   self.assertEqual(rejected.status_code,400)
   self.assertIn('15 students',rejected.json()['detail'])
   fifteen=Path(TEST_DIR.name)/'fifteen.pdf';create_pdf(fifteen,[f'Limit Test {i}' for i in range(15)])
   accepted=client.post('/api/batches',data={'exam_id':eid},files={'file':('fifteen.pdf',fifteen.read_bytes(),'application/pdf')})
   self.assertEqual(accepted.status_code,200,accepted.text)
   limit_id=accepted.json()['id'];deadline=time.time()+120
   while time.time()<deadline:
    limit_batch=client.get(f'/api/batches/{limit_id}').json()
    if limit_batch['status'] in ('ready','failed'):break
    time.sleep(.2)
   self.assertEqual(limit_batch['status'],'ready',limit_batch)
   self.assertEqual(len(limit_batch['papers']),15)
   client.post('/api/logout');self.assertEqual(client.get('/media/papers/'+first['id']+'/0.png').status_code,401)
   self.assertEqual(client.post('/api/login',json={'email':'operator@example.test','password':'wrong'}).status_code,401)
   self.assertEqual(client.post('/api/login',json={'email':'operator@example.test','password':'long-test-password'}).status_code,200)
 def test_scoring(self):
  self.assertEqual(score(KEY,KEY)['total'],100)
  self.assertEqual(score(['-']*25,KEY)['total'],0)
  self.assertEqual(score(['?']*25,KEY)['unresolved'],25)
  with self.assertRaises(ValueError):score(['A'],KEY)

if __name__=='__main__':unittest.main()
