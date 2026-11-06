"""Streaming sandbox and portable run bundle acceptance tests."""
import time
import tempfile
from pathlib import Path
import unittest


class ExperienceTests(unittest.TestCase):
    def test_output_arrives_before_container_finishes(self):
        from server import sandbox
        received=[]
        def emit(name,data):
            received.append((time.monotonic(),name,data))
        code,output=sandbox(['python','-u','-c',"import time;print('first',flush=True);time.sleep(1.2);print('second',flush=True)"],emit)
        chunks=[(t,e['text']) for t,n,e in received if n=='sandbox_output']
        self.assertEqual(code,0)
        self.assertIn('first',output)
        self.assertTrue(chunks,'Sandbox output must be published during execution')
        first=next(t for t,text in chunks if 'first' in text)
        last=next(t for t,text in chunks if 'second' in text)
        self.assertGreater(last-first,.8)
        self.assertEqual(received[-1][2]['status'],'Removed')

    def test_scoped_file_capture_and_plaintext_export(self):
        from run_files import capture
        from reports import plaintext
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'app.py').write_text('def total(x):\n    return x + 1\n')
            (root/'.env').write_text('VULTR_API_KEY=private')
            (root/'link.py').symlink_to(root/'.env')
            bundle=capture(root,['app.py','.env','link.py','../escape.py'],'Original')
        self.assertEqual([f['path'] for f in bundle['files']],['app.py'])
        text=plaintext([{'event':'files',**bundle},{'event':'sandbox_output','name':'test','text':'1 passed\n'},
                        {'event':'result','id':'run','diff':'changed source','verification_tests':{'test_total':'passed'}}])
        self.assertIn('app.py',text);self.assertIn('return x + 1',text)
        self.assertIn('1 passed',text);self.assertIn('changed source',text)
        self.assertNotIn('VULTR_API_KEY=private',text)

    def test_file_capture_has_a_total_byte_limit(self):
        from run_files import capture
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'large.py').write_text('x=1\n'*20000)
            record=capture(root,['large.py'],'Original')
            self.assertLessEqual(sum(len(f['content'].encode()) for f in record['files']),65536)
            self.assertFalse(record['complete'])

if __name__=='__main__':unittest.main(verbosity=2)
