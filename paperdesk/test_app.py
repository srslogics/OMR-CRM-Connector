"""Integration checks with generated scans. Never uses real student records."""
import os,tempfile,time,unittest,io,json
from pathlib import Path
TEST_DIR=tempfile.TemporaryDirectory();os.environ['PAPERDESK_DATA']=TEST_DIR.name
from fastapi.testclient import TestClient
from app import app,db,DATA,process_batch,require_row
from sample import create_pdf,KEY
from processor import score,validate_config,raster,align,detect_question,FIELDS
from student_details import normalise_reviews,details_ready,normalise
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
   self.assertEqual(client.put('/api/papers/'+first['id'],json=review).status_code,400)
   review['field_review']={k:{'status':'verified' if k=='name' else 'blank','value':'First Test' if k=='name' else ''} for k in FIELDS}
   self.assertEqual(client.put('/api/papers/'+first['id'],json=review).status_code,200)
   self.assertEqual(client.put('/api/papers/'+first['id'],json=review).status_code,409)
   self.assertEqual(client.get(f'/api/batches/{bid}/export/xlsx').status_code,200)
   csv=client.get(f'/api/batches/{bid}/export/csv').text
   self.assertIn('First Test',csv);self.assertNotIn('Second Test',csv)
   self.assertTrue(client.get('/api/papers/'+first['id']+'/marksheet').content.startswith(b'%PDF'))
   with db() as c:self.assertEqual(c.execute('SELECT count(*) FROM audit').fetchone()[0],1)
   # Details export is independent of unresolved answers, but never of identity checks.
   pid=third['id'];data=third['data'];fields={k:'' for k in FIELDS};fields.update(name='Reviewed Synthetic Student',school='=FORMULA()',father_mobile='9000012345')
   reviews={k:{'status':'verified' if fields[k] else 'blank','value':fields[k]} for k in FIELDS}
   payload={'answers':data['answers'],'fields':fields,'field_review':reviews,'pairing_verified':True,'approve':False,'version':1}
   self.assertEqual(client.get(f'/media/papers/{pid}/fields/name.png').status_code,200)
   self.assertEqual(client.get(f'/media/papers/{pid}/fields/unknown.png').status_code,404)
   self.assertEqual(client.put(f'/api/papers/{pid}',json=payload).status_code,200)
   self.assertEqual(client.get(f'/api/papers/{pid}').json()['status'],'review')
   exported=client.get(f'/api/batches/{bid}/students/csv');self.assertEqual(exported.status_code,200)
   self.assertIn('Reviewed Synthetic Student',exported.text);self.assertIn("'=FORMULA()",exported.text);self.assertIn('father_mobile status',exported.text);self.assertNotIn('Total /100',exported.text)
   self.assertEqual(client.get(f'/api/batches/{bid}/students/xlsx').status_code,200)
   # Editing a confirmed value without re-confirmation revokes that field's check.
   payload['version']=2;payload['fields']['father_mobile']='9000099999'
   self.assertEqual(client.put(f'/api/papers/{pid}',json=payload).status_code,200)
   changed=client.get(f'/api/papers/{pid}').json();self.assertFalse(changed['details_ready']);self.assertEqual(changed['data']['field_review']['father_mobile']['status'],'pending')
   # A partial phone cannot be marked verified, even by bypassing the browser.
   payload['version']=3;payload['fields']['father_mobile']='12345';payload['field_review']['father_mobile']={'status':'verified','value':'12345'}
   self.assertEqual(client.put(f'/api/papers/{pid}',json=payload).status_code,400)
   # A reread keeps saved manual corrections and has an optimistic version check.
   self.assertEqual(client.post(f'/api/papers/{pid}/extract-details?version=1').status_code,409)
   self.assertEqual(client.post(f'/api/papers/{pid}/extract-details?version=3').status_code,200)
   after=client.get(f'/api/papers/{pid}').json();self.assertEqual(after['data']['fields']['name'],'Reviewed Synthetic Student');self.assertEqual(after['data']['fields']['father_mobile'],'9000099999');self.assertEqual(after['status'],'review')
   # Legacy approvals must acquire the new field checks before release.
   with db() as c:
    legacy=dict(first['data']);legacy['pairing_verified']=True
    c.execute('UPDATE papers SET data=?,status="approved" WHERE id=?',(json.dumps(legacy),first['id']))
   self.assertEqual(client.get(f'/api/papers/{first["id"]}/marksheet').status_code,400)
   self.assertEqual(client.get(f'/api/batches/{bid}/export/csv').status_code,400)
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
   self.assertEqual(client.get(f'/media/papers/{pid}/fields/name.png').status_code,401)
   self.assertEqual(client.get(f'/api/batches/{bid}/students/csv').status_code,401)
   self.assertEqual(client.post(f'/api/papers/{pid}/extract-details?version=4').status_code,401)
   self.assertEqual(client.post('/api/login',json={'email':'operator@example.test','password':'wrong'}).status_code,401)
   self.assertEqual(client.post('/api/login',json={'email':'operator@example.test','password':'long-test-password'}).status_code,200)
 def test_scoring(self):
  self.assertEqual(score(KEY,KEY)['total'],100)
  self.assertEqual(score(['-']*25,KEY)['total'],0)
  self.assertEqual(score(['?']*25,KEY)['unresolved'],25)
  with self.assertRaises(ValueError):score(['A'],KEY)

 def test_detail_verification_rules(self):
  fields={k:'' for k in FIELDS};fields['name']='Synthetic Student'
  reviews={k:{'status':'verified' if k=='name' else 'unreadable','value':fields[k]} for k in FIELDS}
  checked=normalise_reviews(reviews,fields)
  self.assertTrue(details_ready({'fields':fields,'field_review':checked,'pairing_verified':True}))
  self.assertFalse(details_ready({'fields':fields,'field_review':checked,'pairing_verified':False}))
  self.assertEqual(normalise('90 00-012345','father_mobile'),'9000012345')
  self.assertEqual(normalise('9O00012345','father_mobile'),'9O00012345')
  fields['mother_mobile']='123'
  with self.assertRaises(ValueError):normalise_reviews(dict(reviews,mother_mobile={'status':'verified','value':'123'}),fields)
  with self.assertRaises(ValueError):normalise_reviews([],fields)

if __name__=='__main__':unittest.main()
