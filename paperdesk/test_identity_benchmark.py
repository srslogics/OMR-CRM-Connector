import unittest
from identity_benchmark import evaluate
class IdentityBenchmark(unittest.TestCase):
 def test_exact_phone_digits_not_edit_distance(self):
  r=evaluate([{'student':'1','field':'father_mobile','text':'9000012345'}],[{'student':'1','field':'father_mobile','text':'9000012346'}])['father_mobile']
  self.assertEqual(r['exact'],0);self.assertEqual(r['wrong_nonempty'],1)
 def test_names_only_ignore_case_spaces(self):
  refs=[{'student':'1','field':'name','text':'A B'},{'student':'2','field':'name','text':'A B'}]
  preds=[{'student':'1','field':'name','text':'a b'},{'student':'2','field':'name','text':'A D'}]
  self.assertEqual(evaluate(refs,preds)['name']['exact'],1)
 def test_blanks_exclusions_and_missing_are_separate(self):
  refs=[{'student':str(i),'field':'school','text':v} for i,v in enumerate(['',None,'SCHOOL'])]
  preds=[{'student':'0','field':'school','text':'Invented school'}]
  r=evaluate(refs,preds)['school'];self.assertEqual(r['evaluated'],2);self.assertEqual(r['excluded_ambiguous'],1);self.assertEqual(r['false_text_on_blank'],1);self.assertEqual(r['missed_filled'],1)
 def test_duplicate_and_numeric_phone_rejected(self):
  row={'student':'1','field':'name','text':'A'}
  with self.assertRaises(ValueError):evaluate([row,row],[])
  with self.assertRaises(ValueError):evaluate([{'student':'1','field':'father_mobile','text':12345}],[])
 def test_unknown_prediction_rejected(self):
  with self.assertRaises(ValueError):evaluate([],[{'student':'1','field':'name','text':'A'}])
if __name__=='__main__':unittest.main()
