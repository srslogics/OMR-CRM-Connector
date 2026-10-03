"""Geometry and conflict checks independent of private calibration papers."""
import unittest
import cv2
import numpy as np
from page_refinement import refine, merge_reads
from stroke_reader import stroke_evidence, recover
from processor import ink_contrast

class Refinement(unittest.TestCase):
    def test_refinement_rejects_absent_print_and_shape_mismatch(self):
        im=np.full((200,400,3),255,np.uint8)
        self.assertIsNone(refine(im,im,ink_contrast)[0])
        self.assertIsNone(refine(im,im[:100],ink_contrast)[0])

    def test_local_flow_follows_small_smooth_page_distortion(self):
        im=np.full((450,650,3),255,np.uint8)
        for y in range(50,400,40):
            cv2.putText(im,'Printed question 123 ABC',(40,y),0,.7,(20,20,20),2)
        yy,xx=np.mgrid[:450,:650].astype('float32')
        scan=cv2.remap(im,xx+4*np.sin(yy/110),yy,cv2.INTER_LINEAR,borderValue=(255,255,255))
        actual,info=refine(scan,im,ink_contrast)
        self.assertIsNotNone(actual);self.assertTrue(info['accepted'])
        self.assertLess(np.mean(abs(actual.astype(float)-im)),np.mean(abs(scan.astype(float)-im)))

    def test_alignment_conflict_cannot_replace_existing_answer(self):
        a={0:{'answer':'A','confidence':'strong'},1:{'answer':'?','suggested_answer':'C'}}
        b={0:{'answer':'B','confidence':'strong'},1:{'answer':'B','confidence':'strong'}}
        d=merge_reads(a,b)
        self.assertEqual(d[0]['answer'],'?');self.assertEqual(d[1]['answer'],'?')
        self.assertEqual(a[0]['answer'],'A')

    def fixture(self):
        im=np.full((350,1100,3),255,np.uint8);boxes=[]
        for i in range(4):
            y=60+65*i
            cv2.rectangle(im,(500,y),(516,y+16),(30,30,30),1)
            boxes.append([495/1100,(y-5)/350,30/1100,28/350])
        return im,boxes

    def tick(self,im,option):
        y=60+65*option
        cv2.line(im,(497,y+7),(507,y+21),(40,40,40),2)
        cv2.line(im,(507,y+21),(575,y-19),(40,40,40),2)

    def test_long_tail_is_anchored_to_its_turning_point(self):
        master,boxes=self.fixture();scan=master.copy();self.tick(scan,2)
        d=stroke_evidence(scan,master,boxes,ink_contrast)
        self.assertEqual(d['answer'],'C')

    def test_multiple_long_ticks_are_not_resolved_by_length(self):
        master,boxes=self.fixture();scan=master.copy();self.tick(scan,1);self.tick(scan,2)
        d=stroke_evidence(scan,master,boxes,ink_contrast)
        self.assertEqual(d['answer'],'?')
        merged=recover({'answer':'C','confidence':'strong'},[d,d,d])
        self.assertEqual(merged['answer'],'?')

    def test_long_tick_and_short_crossout_veto_strong_box_read(self):
        evidence={'answer':'?','marks':[{'option':1,'long':True},{'option':2,'long':False}]}
        result=recover({'answer':'C','confidence':'strong'},[evidence,evidence,evidence])
        self.assertEqual(result['answer'],'?');self.assertEqual(result['confidence'],'review')

    def test_stroke_consensus_preserves_disagreement_and_review(self):
        a={'answer':'B','marks':[]};b={'answer':'C','marks':[]}
        self.assertEqual(recover({'answer':'?'},[a,b,a])['answer'],'?')
        d=recover({'answer':'?'},[a,a,a])
        self.assertEqual(d['answer'],'B');self.assertEqual(d['confidence'],'review')
        self.assertEqual(recover({'answer':'A'},[a,a,a])['answer'],'?')
        self.assertEqual(recover({'answer':'?','suggested_answer':'C'},[a,a,a])['answer'],'?')

if __name__=='__main__':unittest.main()
