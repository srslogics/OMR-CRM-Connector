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
 def test_strong_evidence_is_stable_and_not_a_percentage(self):
  master,regions=self.fixture();scan=master.copy();self.tick(scan,2,color=(90,90,90))
  d=detect_question(scan,master,regions)
  self.assertEqual(d['answer'],'C');self.assertEqual(d['confidence'],'strong')
  self.assertEqual(len(d['checkbox_evidence']),4)
  self.assertEqual(len(d['checkbox_evidence'][2]['pixels_by_threshold']),3)
 def test_missing_competing_box_prevents_strong_label(self):
  master,regions=self.fixture();scan=master.copy();self.tick(scan,2,color=(90,90,90))
  x,y,w,h=regions[0];scan[int(y*350):int((y+h)*350),int(x*1100):int((x+w)*1100)]=255
  self.assertNotEqual(detect_question(scan,master,regions)['confidence'],'strong')
 def test_option_text_suggestion_is_not_scored(self):
  from unittest.mock import patch
  import processor
  master,regions=self.fixture()
  weak={'answer':'?','confidence':'review','reason':'No checkbox mark','evidence':[]}
  values=[{'v':[30,25,20] if i==1 else [0,0,0],'cost':.1,'shift':[0,0],'left':450,'limit':7} for i in range(4)]
  with patch.object(processor,'detect_checkbox_question',return_value=weak),patch.object(processor,'option_evidence',side_effect=values):
   d=detect_question(master,master,regions)
  self.assertEqual(d['answer'],'?');self.assertEqual(d['suggested_answer'],'B')
 def test_weak_checkbox_with_competing_option_ink_abstains(self):
  from unittest.mock import patch
  import processor
  master,regions=self.fixture()
  values=[{'v':[30,25,20] if i in (1,2) else [0,0,0],'cost':.1,'shift':[0,0],'left':450,'limit':7} for i in range(4)]
  with patch.object(processor,'detect_checkbox_question',return_value={'answer':'B','confidence':'review','reason':'Weak mark'}),patch.object(processor,'option_evidence',side_effect=values):
   self.assertEqual(detect_question(master,master,regions)['answer'],'?')
 def test_valid_zero_is_still_allowed_after_review(self):
  self.assertEqual(score(['B']*25,['A']*25)['total'],0)
  self.assertEqual(score(['-']*25,['A']*25)['total'],0)

if __name__=='__main__':unittest.main()
