import unittest
from operations import pending_items
from processor import FIELDS

class Operations(unittest.TestCase):
    def row(self):
        fields={k:'Value' for k in FIELDS}
        return {'id':'p','batch_id':'b','batch_name':'Batch','exam_name':'Exam','idx':2,'start_page':30,'status':'review',
                'data':{'fields':fields,'answers':['A']*25,'details':[{'answer':'A','confidence':'strong'}]*25,
                        'field_review':{k:{'value':v,'status':'verified'} for k,v in fields.items()},'pairing_verified':True}}
    def test_source_page_offset_and_ready_status(self):
        p=pending_items(self.row())
        self.assertEqual(p['student'],18);self.assertEqual(p['source_pages'],[35,36]);self.assertTrue(p['ready_for_approval'])
    def test_stale_confirmation_and_changed_answer_return_to_team(self):
        r=self.row();r['data']['answers'][0]='B';r['data']['fields']['name']='Changed';r['data']['pairing_verified']=False
        p=pending_items(r)
        self.assertEqual(p['answers'],[1]);self.assertEqual(p['fields'],['name']);self.assertTrue(p['pairing_required']);self.assertFalse(p['ready_for_approval'])
    def test_unknown_is_not_confirmable_and_approved_is_excluded(self):
        r=self.row();r['data']['answers'][0]='?';r['data']['answer_checks']={'0':'?'}
        self.assertEqual(pending_items(r)['answers'],[1])
        r=self.row();r['status']='approved';self.assertIsNone(pending_items(r))
    def test_no_student_values_in_queue(self):
        self.assertNotIn('Value',str(pending_items(self.row())))

if __name__=='__main__':unittest.main()
