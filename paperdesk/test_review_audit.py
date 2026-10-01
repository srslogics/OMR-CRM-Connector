import unittest
from review_audit import comparison

class ReviewAudit(unittest.TestCase):
    def test_missing_history_is_not_perfect_accuracy(self):
        d={'answers':['A']*25,'fields':{},'field_review':{}}
        report=comparison([{'status':'approved','data':d}])
        self.assertEqual(report['answers']['unavailable'],25)
        self.assertEqual(report['answers']['total'],0)
    def test_counts_uncertain_separately_and_ignores_unapproved(self):
        d={'answers':['A']*25,'detected_answers':['?','B']+['A']*23,
           'fields':{'name':'Test Name'},'field_review':{'name':{'status':'verified','value':'Test Name'}},
           'field_ocr':{'name':{'suggested':'test name'}}}
        report=comparison([{'status':'approved','data':d},{'status':'review','data':d}])
        self.assertEqual(report['approved_students'],1)
        self.assertEqual(report['answers']['matched'],23)
        self.assertEqual(report['answers']['different'],1)
        self.assertEqual(report['answers']['unresolved'],1)
        self.assertEqual(report['fields']['name']['matched'],1)
        self.assertEqual(len(report['students'][0]['answers']),2)
        self.assertEqual(report['students'][0]['answers'][1]['reviewed'],'A')
    def test_student_index_preserved_and_field_values_not_exposed_in_log(self):
        d={'answers':['A']*25,'detected_answers':['A']*25,
           'fields':{'name':'Private Name'},'field_review':{'name':{'status':'verified','value':'Private Name'}},
           'field_ocr':{'name':{'suggested':'Incorrect Name'}}}
        report=comparison([{'idx':4,'status':'approved','data':d}])
        self.assertEqual(report['students'][0]['student'],5)
        self.assertEqual(report['students'][0]['fields'],['name'])
        self.assertNotIn('Private Name',str(report))
