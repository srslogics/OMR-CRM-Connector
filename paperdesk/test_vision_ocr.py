import unittest
from unittest.mock import patch
import numpy as np
from vision_ocr import clean_output,merge_reading,transcribe,refine_name_reading

class VisionOCR(unittest.TestCase):
    def reading(self):
        return {'suggested':'OLD NAME','state':'review','engine':'local','candidates':[{'text':'OLD NAME','score':.8,'method':'original'}]}
    def test_disabled_reader_does_not_load_model(self):
        with patch.dict('os.environ',{'PAPERDESK_VISION_MODEL_DIR':''}),patch('vision_ocr.engine') as engine:
            self.assertIsNone(transcribe(np.zeros((20,20,3),dtype=np.uint8)));engine.assert_not_called()
    def test_literal_text_only_and_blank(self):
        self.assertEqual(clean_output('```text\nABC\n```'),'ABC')
        self.assertEqual(clean_output('BLANK'),'');self.assertIsNone(clean_output('{"name":"ABC"}'))
        self.assertIsNone(clean_output('first\nsecond'))
    def test_disagreement_retains_both_and_never_confirms(self):
        old=self.reading();out=merge_reading(old,'NEW NAME','name')
        self.assertEqual(out['suggested'],'NEW NAME');self.assertEqual(out['state'],'conflict')
        self.assertEqual(len(out['candidates']),2);self.assertEqual(old['suggested'],'OLD NAME')
        self.assertNotIn('verified',out)
    def test_phone_section_and_blank_are_not_replaced(self):
        for field in ('father_mobile','mother_mobile','section'):
            self.assertEqual(merge_reading(self.reading(),'1234567890',field)['suggested'],'OLD NAME')
        old=self.reading();old['suggested']=''
        self.assertEqual(merge_reading(old,'Invented Name','name')['suggested'],'')
        self.assertEqual(merge_reading(self.reading(),'1b','class')['suggested'],'OLD NAME')
    def test_name_refinement_preserves_alternatives_and_blank(self):
        old=self.reading();out=refine_name_reading(old,'NEW NAME')
        self.assertEqual(out['suggested'],'NEW NAME');self.assertEqual(out['state'],'conflict')
        self.assertEqual(old['suggested'],'OLD NAME');self.assertEqual(len(out['candidates']),2)
        old['suggested']='';self.assertEqual(refine_name_reading(old,'GUESS')['suggested'],'')
        self.assertEqual(refine_name_reading(self.reading(), '')['suggested'],'OLD NAME')

    def test_agreement_is_not_verification(self):
        out=merge_reading(self.reading(),'old name','name')
        self.assertTrue(out['reader_agreement']);self.assertEqual(out['state'],'review')
        self.assertEqual(len(out['candidates']),1)

if __name__=='__main__':unittest.main()
