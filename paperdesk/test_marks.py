"""Answer reading must be scan-based, tolerate faint ink, and abstain safely."""
import unittest
import cv2
import numpy as np
from processor import detect_question,reread_data,score

class MarkReading(unittest.TestCase):
 def fixture(self):
  image=np.full((350,1100,3),235,np.uint8);regions=[]
  for i in range(4):
   y=65+55*i
   cv2.rectangle(image,(500,y),(517,y+17),(70,70,70),1)
   cv2.putText(image,'ABCD'[i],(460,y+14),cv2.FONT_HERSHEY_SIMPLEX,.5,(70,70,70),1)
   regions.append([496/1100,(y-5)/350,40/1100,29/350])
  return image,regions
 def tick(self,image,i,color=(184,184,184)):
  y=65+55*i
  cv2.line(image,(504,y+9),(509,y+14),color,2)
  cv2.line(image,(509,y+14),(530,y-8),color,2)
 def test_faint_tick_above_old_fixed_darkness_limit(self):
  master,regions=self.fixture();scan=master.copy();self.tick(scan,2)
  self.assertEqual(detect_question(scan,master,regions)['answer'],'C')
 def test_shadow_and_small_translation(self):
  master,regions=self.fixture();scan=master.copy();self.tick(scan,1)
  gradient=np.linspace(.7,1.,1100)[None,:,None]
  scan=(scan*gradient).astype('uint8')
  scan=cv2.warpAffine(scan,np.float32([[1,0,2],[0,1,-2]]),(1100,350),borderValue=(255,255,255))
  self.assertEqual(detect_question(scan,master,regions)['answer'],'B')
 def test_two_marks_require_review(self):
  master,regions=self.fixture();scan=master.copy();self.tick(scan,0);self.tick(scan,2)
  self.assertEqual(detect_question(scan,master,regions)['answer'],'?')
 def test_no_evidence_is_not_an_automatic_blank(self):
  master,regions=self.fixture()
  self.assertEqual(detect_question(master,master,regions)['answer'],'?')
  self.assertEqual(detect_question(np.full_like(master,255),master,regions)['answer'],'?')
 def test_reread_keeps_manual_choices_and_details(self):
  old={'answers':['D']*25,'answer_overrides':[2],'fields':{'name':'Reviewed name'},'field_review':{'name':{'status':'verified','value':'Reviewed name'}},'pairing_verified':True}
  detected=[{'answer':'A','reason':'test','evidence':[]} for _ in range(25)]
  new=reread_data(old,detected,['A']*25,protected=[3])
  self.assertEqual(new['answers'][:5],['A','A','D','D','A'])
  self.assertEqual(new['fields'],old['fields']);self.assertEqual(new['field_review'],old['field_review'])
  self.assertTrue(new['pairing_verified']);self.assertEqual(new['score']['total'],92)
 def test_valid_zero_is_still_allowed_after_review(self):
  self.assertEqual(score(['B']*25,['A']*25)['total'],0)
  self.assertEqual(score(['-']*25,['A']*25)['total'],0)

if __name__=='__main__':unittest.main()
