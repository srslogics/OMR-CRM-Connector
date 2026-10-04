import unittest,copy
from student_results import result_row

class StudentResults(unittest.TestCase):
 def row(self,total=40,reason='Local alignment is uncertain; inspect the original scan.',count=1):
  return {'status':'review','data':{'fields':{'name':'TEST','school':'SCHOOL','father_mobile':'9000012345'},'score':{'total':total},'answers':['?']*count,'details':[{'reason':reason} for _ in range(count)]}}
 def test_grace_once_and_no_mutation(self):
  row=self.row(count=9);old=copy.deepcopy(row);result=result_row(row)
  self.assertEqual(result['marks'],48);self.assertEqual(result['grace'],8);self.assertEqual(row,old)
 def test_cap(self):self.assertEqual(result_row(self.row(96))['marks'],100)
 def test_no_grace_for_blank_or_conflict(self):
  for reason in ['No reliable mark found; confirm a blank from the scan.','Multiple marks or correction; review the scan.']:
   self.assertEqual(result_row(self.row(reason=reason))['marks'],40)
 def test_resolved_alignment_not_awarded(self):
  row=self.row();row['data']['answers']=['B'];self.assertEqual(result_row(row)['grace'],0)
 def test_only_client_columns(self):
  result=result_row(self.row());self.assertNotIn('id',result);self.assertNotIn('answers',result);self.assertEqual(result['details_status'],'Not verified');self.assertEqual(result['result_status'],'Provisional')

if __name__=='__main__':unittest.main()
