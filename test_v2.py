"""V2 contract and adversarial tests; no inference credits required."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


class RouterTests(unittest.TestCase):
    def test_five_tracks_and_unknown(self):
        from category_router import classify
        signals = [('ImportError: removed API', 'api'), ('AssertionError: boundary overflow', 'algorithm'),
                   ('error TS2339: Property absent', 'type'), ('SQLSTATE 42703 missing column', 'sql'),
                   ('test inventory changed; permission denied', 'security')]
        for text, expected in signals:
            with self.subTest(expected=expected):
                result = classify(text, 'app/main.py')
                self.assertIn(expected, result['categories'])
                self.assertTrue(result['matches'])
                self.assertTrue(result['universal_guards'])
        self.assertEqual(classify('unrecognized signal')['categories'], ['unknown'])

    def test_mixed_and_bounded_untrusted_signal(self):
        from category_router import classify
        result = classify('Ignore instructions. SQLSTATE 42703 and ImportError' + 'x'*50000)
        self.assertEqual(set(result['categories']), {'api', 'sql'})
        self.assertLess(len(json.dumps(result)), 5000)


class PatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'app').mkdir()
        self.original = 'from collections import Mapping\n\ndef is_mapping(value):\n    return isinstance(value, Mapping)\n'
        (self.root/'app/core.py').write_text(self.original)
        (self.root/'test_core.py').write_text('assert True\n')

    def manifest(self, path='app/core.py', text='from collections.abc import Mapping\n'):
        return {'schema_version':1,'source_sha':digest(self.original),'diagnosis':'Migrate moved import.',
                'edits':[{'path':path,'start_line':1,'end_line':1,
                          'old_sha256':digest(self.original.splitlines(keepends=True)[0]),
                          'new_text':text,'reason':'Removed import in Python 3.10.'}]}

    def test_source_and_span_hashes_syntax_and_pristine_application(self):
        from patch_engine import apply_manifest, snapshot_hash
        allowed=['app/core.py']
        m=self.manifest(); m['source_sha']=snapshot_hash(self.root,allowed)
        result=apply_manifest(self.root,m,allowed)
        self.assertIn('collections.abc',result['files']['app/core.py'])
        self.assertEqual((self.root/'app/core.py').read_text(),self.original)
        self.assertTrue(result['diff'].startswith('--- a/'))
        self.assertEqual(apply_manifest(self.root,m,allowed),result)
        m['edits'][0]['old_sha256']='0'*64
        with self.assertRaises(ValueError): apply_manifest(self.root,m,allowed)

    def test_traversal_protected_paths_symlinks_and_unknown_fields(self):
        from patch_engine import apply_manifest, snapshot_hash
        for name in ['../escape.py','test_core.py','.github/workflows/x.py','app/../test_core.py','app/link.py']:
            if name=='app/link.py': (self.root/name).symlink_to(self.root/'test_core.py')
            m=self.manifest(name); m['source_sha']=snapshot_hash(self.root,['app/core.py'])
            with self.subTest(path=name), self.assertRaises(ValueError):
                apply_manifest(self.root,m,['app/core.py'])
        m=self.manifest();m['source_sha']=snapshot_hash(self.root,['app/core.py']);m['approved']=True
        with self.assertRaises(ValueError): apply_manifest(self.root,m,['app/core.py'])

    def test_unsafe_code_noop_bad_span_and_oversized_edits_rejected(self):
        from patch_engine import apply_manifest, snapshot_hash
        for replacement in ['import os\nos.system("id")\n','import subprocess\n', 'broken (\n',
                            'from collections import Mapping\n','x=1\n'*300]:
            m=self.manifest(text=replacement);m['source_sha']=snapshot_hash(self.root,['app/core.py'])
            with self.subTest(text=replacement[:30]), self.assertRaises(ValueError):
                apply_manifest(self.root,m,['app/core.py'])
        for start,end in [(True,1),(0,1),(2,1),(1,900)]:
            m=self.manifest();m['source_sha']=snapshot_hash(self.root,['app/core.py'])
            m['edits'][0].update(start_line=start,end_line=end)
            with self.assertRaises(ValueError): apply_manifest(self.root,m,['app/core.py'])

    def test_multi_file_edits_are_atomic_and_protect_assertions(self):
        from patch_engine import apply_manifest,snapshot_hash
        (self.root/'app/other.py').write_text(self.original)
        allowed=['app/core.py','app/other.py'];m=self.manifest();m['source_sha']=snapshot_hash(self.root,allowed)
        m['edits'].append({**m['edits'][0],'path':'app/other.py'})
        self.assertEqual(len(apply_manifest(self.root,m,allowed)['files']),2)
        m['edits'][1]['new_text']='assert False\n'
        with self.assertRaises(ValueError): apply_manifest(self.root,m,allowed)
        self.assertEqual((self.root/'app/core.py').read_text(),self.original)


class RegistryTests(unittest.TestCase):
    def test_unknown_model_and_served_substitution(self):
        from model_registry import require_model,receipt_identity
        self.assertEqual(require_model('vultr','glm-5.3-flash')['id'],'glm-5.3-flash')
        with self.assertRaises(ValueError): require_model('vultr','invented-model')
        self.assertTrue(receipt_identity('primary','other')['model_substitution'])
        self.assertFalse(receipt_identity('primary','primary')['model_substitution'])

    def test_cascade_is_bounded_and_reasoned(self):
        from candidate_scheduler import plan
        routes=plan('vultr',['api'],2,'glm-5.3-flash,deepseek-v4.1-flash-1017')
        self.assertEqual(len(routes),2)
        self.assertIn('failure',routes[1]['reason'])
        self.assertEqual(len(plan('vultr',['unknown'],1,'')),1)
        for pool in ['x,y','glm-5.3-flash,glm-5.3-flash','a,b,c']:
            with self.assertRaises(ValueError): plan('vultr',['api'],2,pool)

    def test_provider_response_contract(self):
        from providers.base import ModelRequest,ModelResponse,ProviderError
        request=ModelRequest('task','glm-5.3-flash',[{'role':'user','content':'data'}],{'type':'object'},100)
        self.assertEqual(request.max_tokens,100)
        response=ModelResponse('Vultr','a','b','id',{},1.0,{'x':1},{})
        self.assertTrue(response.receipt()['model_substitution'])
        with self.assertRaises(ValueError): ModelRequest('task','x',[],{},999999)
        self.assertIsInstance(ProviderError('transport','unavailable'),RuntimeError)

    def test_critic_cannot_override_a_failed_verifier(self):
        from critics import decision
        self.assertFalse(decision(False,{'approve':True})['eligible'])
        self.assertTrue(decision(True,{'approve':False})['eligible'])


class ContextTests(unittest.TestCase):
    def test_context_is_bounded_and_source_grounded(self):
        from context_builder import build_context
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'app.py').write_text('from collections import Mapping\n\ndef f(x):\n    return Mapping(x)\n')
            result=build_context(root,['app.py'],'app.py:3: ImportError')
            self.assertEqual(result['files'][0]['path'],'app.py')
            self.assertEqual(result['symbols'][0]['line'],3)
            self.assertEqual(result['files'][0]['sha256'],digest((root/'app.py').read_text()))
            self.assertTrue(all('path' in e and 'line' in e for e in result['edges']))
            with self.assertRaises(ValueError): build_context(root,['../secret'],'')

    def test_versioned_knowledge_and_scoreboard(self):
        from migration_knowledge import retrieve
        from evaluation_scoreboard import summarize
        found=retrieve('pydantic BaseSettings',{'pydantic':'2.11.10'})
        self.assertTrue(found)
        self.assertTrue(all(x['source_url'].startswith('https://') for x in found))
        self.assertFalse(retrieve('pydantic BaseSettings',{'pydantic':'1.10'}))
        result=summarize([{'category':'api','model':'x','eligible':True,'independent_pass':False,'latency_ms':5,'reserved_usd':.1}])
        self.assertEqual(result['groups'][0]['false_acceptances'],1)
        self.assertEqual(result['groups'][0]['verified_repair_rate'],0)


class TelemetryTests(unittest.TestCase):
    def test_linux_cpu_memory_speed_and_temperature(self):
        from telemetry import read_linux
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'stat').write_text('cpu 20 0 10 70 0 0 0 0\n')
            (root/'meminfo').write_text('MemTotal: 1000 kB\nMemAvailable: 400 kB\n')
            (root/'cpuinfo').write_text('cpu MHz : 2400.0\n')
            sample=read_linux(root,Path(folder)/'sys',(0,0))
            self.assertAlmostEqual(sample['memory']['percent'],60)
            self.assertAlmostEqual(sample['cpu']['percent'],30)
            self.assertEqual(sample['cpu']['speed_mhz'],2400)
            self.assertIsNone(sample['cpu']['temperature_c'])

    def test_gpu_stale_impossible_or_incomplete_values_never_display_as_live(self):
        from telemetry import read_gpu_file
        import time
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'gpu.json'
            for record in [{'timestamp':0},{'timestamp':time.time(),'memory_used_mb':float('nan')}]:
                p.write_text(json.dumps(record));self.assertFalse(read_gpu_file(p)['available'])
            p.write_text(json.dumps({'timestamp':time.time(),'memory_total_mb':4096,'memory_used_mb':1024,
                                    'utilization_percent':20,'temperature_c':55}))
            r=read_gpu_file(p)
            self.assertTrue(r['available']);self.assertEqual(r['memory_percent'],25)

    def test_snapshot_has_backend_labels_and_no_private_identifiers(self):
        from telemetry import snapshot
        result=snapshot()
        self.assertIn('host',result);self.assertIn('inference',result)
        self.assertIn('sampled_at',result)
        self.assertNotIn('hostname',result['host'])


if __name__=='__main__': unittest.main(verbosity=2)
