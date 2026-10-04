import copy
import unittest
from unittest.mock import patch
import numpy as np
import learned_marks as reader

class LearnedMarks(unittest.TestCase):
    def fixture(self):
        template=np.zeros((4,5,3),np.uint8);mapping={'1':{'page':0,'boxes':[[0,0,.1,.1]]*4}}
        model={'id':'test','threshold':.75,'secondary_cap':.15,'scopes':[reader.scope_hash(mapping,0,template)]}
        detail={'answer':'?','reason':'Faint ink','local_registration':{'accepted':True},
                'second_resolution':{},'whole_option_color':[[0]*3]*4,'stroke_reads':[]}
        return template,mapping,model,detail

    def run_reader(self,detail,scores=(.02,.9,.01,.02),mismatch=False):
        image,mapping,model,_=self.fixture()
        if mismatch:image[0,0,0]=1
        with patch.object(reader,'load_model',return_value=(model,[])),patch.object(reader,'predict',return_value=np.array(scores)):
            return reader.recover_page({0:detail},mapping,0,image)[0]

    def test_recovered_answer_is_never_a_verified_answer(self):
        *_,d=self.fixture();before=copy.deepcopy(d);out=self.run_reader(d)
        self.assertEqual(out['answer'],'B');self.assertEqual(out['confidence'],'review')
        self.assertIn('learned_reader',out);self.assertEqual(d,before)

    def test_unknown_template_or_missing_alignment_cannot_use_model(self):
        *_,d=self.fixture();self.assertEqual(self.run_reader(d,mismatch=True)['answer'],'?')
        d['local_registration']['accepted']=False
        self.assertEqual(self.run_reader(d)['answer'],'?')

    def test_blank_correction_disagreement_and_competing_options_stay_unresolved(self):
        for reason in ('No reliable mark found','Separate checkmark strokes','Readers disagree','Marks disagree','Multiple marks or correction'):
            *_,d=self.fixture();d['reason']=reason
            self.assertEqual(self.run_reader(d)['answer'],'?')
        *_,d=self.fixture();self.assertEqual(self.run_reader(d,(.5,.9,.01,.02))['answer'],'?')
        for key in ('suggested_answer','second_resolution','local_read'):
            *_,d=self.fixture();d[key]='C' if key=='suggested_answer' else {'answer':'C'}
            self.assertEqual(self.run_reader(d)['answer'],'?')

    def test_existing_answers_and_human_checks_are_unchanged(self):
        *_,d=self.fixture();d.update(answer='A',confidence='strong',human_check='A')
        self.assertEqual(self.run_reader(d),d)

    def test_features_exclude_identity_key_question_and_answer_labels(self):
        *_,d=self.fixture();a=reader.option_features(d)
        d.update(name='Someone',question=25,key=['D']*25,reviewed_answer='A',answer='C')
        np.testing.assert_array_equal(a,reader.option_features(d))
        self.assertEqual(a.shape,(4,120))

    def test_packaged_forest_is_finite_bounded_and_numeric(self):
        model,trees=reader.load_model();scores=reader.predict(np.zeros((4,120)),trees)
        self.assertEqual(len(trees),300);self.assertFalse(model['automatic_release_validated'])
        self.assertTrue(np.isfinite(scores).all());self.assertTrue(((scores>=0)&(scores<=1)).all())
        with self.assertRaises(ValueError):reader.predict(np.full((4,120),np.nan),trees)

if __name__=='__main__':unittest.main()
