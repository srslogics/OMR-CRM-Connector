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
