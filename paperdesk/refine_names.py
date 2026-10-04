"""Resumable local name reread. Retains human edits and records every change."""
import argparse,json,time
import cv2
from storage import db,read_db,DATA,materialize
from student_details import clean_grid
from vision_ocr import configured,transcribe,refine_name_reading

def run(import_id,email):
    if not configured():raise RuntimeError('Configure the local vision model first')
    with read_db() as c:
        operator=c.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()
        if not operator:raise ValueError('Existing operator account required')
        rows=c.execute('SELECT p.* FROM papers p JOIN bulk_parts bp ON bp.batch_id=p.batch_id WHERE bp.import_id=? ORDER BY bp.start_page,p.idx',(import_id,)).fetchall()
    changed=skipped=0
    for row in rows:
        old=json.loads(row['data']);reading=old.get('field_ocr',{}).get('name',{});value=old.get('fields',{}).get('name','')
        reviewed=old.get('field_review',{}).get('name',{}).get('status') in {'verified','blank','unreadable'}
        if row['status']=='approved' or reviewed or not value or value!=reading.get('suggested') or 'name_grid_vision' in reading:
            skipped+=1;continue
        image=cv2.imread(str(materialize(DATA/'batches'/row['batch_id']/f'{row["idx"]}-field-name.png')))
        if image is None:skipped+=1;continue
        text=transcribe(clean_grid(image))
        if text is None:
            import vision_ocr
            if vision_ocr._failed:raise RuntimeError('Name reader unavailable; no further changes applied')
            skipped+=1;continue
        refined=refine_name_reading(reading,text);new={**old,'fields':{**old['fields'],'name':refined['suggested']},'field_ocr':{**old['field_ocr'],'name':refined},'field_review':{**old.get('field_review',{}),'name':{'status':'pending','value':refined['suggested']}}}
        with db() as c:
            encoded=json.dumps(new)
            result=c.execute("UPDATE papers SET data=?,version=version+1 WHERE id=? AND version=? AND status!='approved'",(encoded,row['id'],row['version']))
            if result.rowcount==1:
                c.execute('INSERT INTO audit(paper_id,user_id,at,before_data,after_data) VALUES(?,?,?,?,?)',(row['id'],operator['id'],time.time(),row['data'],encoded));changed+=1
            else:skipped+=1
        if (changed+skipped)%10==0:print('Name records refreshed:',changed,'skipped/protected:',skipped,flush=True)
    print('Finished. Name records refreshed:',changed,'skipped/protected:',skipped,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--import-id',required=True);p.add_argument('--operator-email',required=True);a=p.parse_args();run(a.import_id,a.operator_email)
