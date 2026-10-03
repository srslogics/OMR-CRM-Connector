"""Real spawned-process parity and checkpoint recovery on synthetic scans."""
import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

class ParallelWorker(unittest.TestCase):
    def test_spawned_workers_resume_without_replacing_reviewed_record(self):
        if os.environ.get('DATABASE_URL'):
            self.skipTest('Requires isolated local storage')
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'PAPERDESK_DATA':tmp,'PAPERDESK_EMBEDDED_WORKER':'0'}):
            # Run in a fresh interpreter: app/storage settings are import-time.
            import subprocess, sys
            result=subprocess.run([sys.executable,str(Path(__file__).with_name('worker_test_scenario.py')),tmp],capture_output=True,text=True,timeout=120)
            self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
            self.assertIn('PARITY_AND_RESUME_OK',result.stdout)

if __name__=='__main__':unittest.main()
