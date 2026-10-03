import unittest
import cv2
import test_marks
from whole_option import supplement

class WholeOption(unittest.TestCase):
    def fixture(self):
        master,regions=test_marks.MarkReading().fixture();scan=master.copy()
        cv2.line(scan,(100,125),(107,132),(160,40,40),2)
        cv2.line(scan,(107,132),(120,114),(160,40,40),2)
        return master,scan,regions
    def test_recovers_off_box_blue_tick_without_key(self):
        master,scan,regions=self.fixture()
        d=supplement({'answer':'?','reason':'No reliable mark found'},scan,master,regions)
        self.assertEqual(d['answer'],'B');self.assertEqual(d['confidence'],'review')
    def test_mixed_ink_conflict_veto(self):
        master,scan,regions=self.fixture()
        for reading in ({'answer':'?','reason':'Ink at multiple option positions'},
                        {'answer':'?','reason':'Different resolutions disagree'},
                        {'answer':'C','reason':'Gray mark'},
                        {'answer':'?','reason':'No mark','checkbox_evidence':[{'pixels_by_threshold':[20,18,17]},None,None,None]},
                        {'answer':'?','reason':'No mark','second_resolution':{'answer':'D'}}):
            with self.subTest(reading=reading):
                self.assertEqual(supplement(reading,scan,master,regions)['answer'],reading['answer'])
    def test_coloured_master_print_is_not_a_pen_mark(self):
        master,scan,regions=self.fixture()
        self.assertEqual(supplement({'answer':'?','reason':'No mark'},scan,scan,regions)['answer'],'?')
    def test_multiple_blue_choices_abstain(self):
        master,scan,regions=self.fixture()
        cv2.line(scan,(100,180),(107,187),(160,40,40),2)
        cv2.line(scan,(107,187),(120,169),(160,40,40),2)
        self.assertEqual(supplement({'answer':'?','reason':'No mark'},scan,master,regions)['answer'],'?')
if __name__=='__main__':unittest.main()
