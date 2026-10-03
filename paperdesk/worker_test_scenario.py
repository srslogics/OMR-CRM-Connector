"""Subprocess fixture for test_parallel_worker; synthetic records only."""
import os
import json
from pathlib import Path
from unittest.mock import patch

def main():
    from fastapi.testclient import TestClient
    import app as service
    from sample import create_pdf
    root=Path(os.environ['PAPERDESK_DATA'])
    with TestClient(service.app) as client:
        client.post('/api/setup',json={'name':'Worker QA','email':'worker@example.test','password':'synthetic-password'})
        eid=client.post('/api/exams',json={'name':'Parallel QA','class_name':'10'}).json()['id']
        master=root/'blank.pdf';config=create_pdf(master)
        assert client.post(f'/api/exams/{eid}/template',files={'file':('blank.pdf',master.read_bytes(),'application/pdf')}).status_code==200
        assert client.put(f'/api/exams/{eid}',json=config).status_code==200
        assert client.post(f'/api/exams/{eid}/lock').status_code==200
        scans=root/'scans.pdf';create_pdf(scans,['One','Two','Three','Four','Five'])
        result=client.post('/api/bulk-imports',data={'exam_id':eid,'pairing_confirmed':'true'},files={'file':('scans.pdf',scans.read_bytes(),'application/pdf')})
        assert result.status_code==200,result.text
        bid=result.json()['batches'][0]['batch_id']
        def rows():
            with service.read_db() as c:return [dict(r) for r in c.execute('SELECT * FROM papers WHERE batch_id=? ORDER BY idx',(bid,))]
        os.environ['PAPERDESK_PROCESS_WORKERS']='1'
        service.process_batch(service.require_row('batches',bid));baseline=rows()
        with service.db() as c:
            c.execute('DELETE FROM papers WHERE batch_id=? AND idx>0',(bid,))
            c.execute("UPDATE papers SET status='approved' WHERE batch_id=? AND idx=0",(bid,))
        preserved=rows()[0]
        original=service.commit_inferred
        def interrupt(*args):
            original(*args);service.stop.set()
        os.environ['PAPERDESK_PROCESS_WORKERS']='2'
        with patch.object(service,'commit_inferred',side_effect=interrupt):service.process_batch(service.require_row('batches',bid))
        partial=rows()
        assert len(partial)==3,len(partial) # one prior plus bounded two in flight
        assert partial[0]==preserved
        assert service.require_row('batches',bid)['status']=='processing'
        service.stop.clear();service.process_batch(service.require_row('batches',bid));actual=rows()
        assert len(actual)==5 and actual[0]==preserved
        for expected,observed in zip(baseline,actual):
            a,b=json.loads(expected['data']),json.loads(observed['data'])
            for key in ('answers','fields','score','detected_answers'):assert a[key]==b[key],(key,a[key],b[key])
        assert service.require_row('batches',bid)['status']=='ready'
        assert service.require_row('batches',bid)['done']==5
        print('PARITY_AND_RESUME_OK')

if __name__=='__main__':main()
