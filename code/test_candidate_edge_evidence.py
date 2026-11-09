"""Evidence-schema software fixtures only; artificial PASS reports are not scientific audits."""
import json
import tempfile
import unittest
from pathlib import Path
from candidate_edge_evidence import authorize,edge_fingerprint,ROLES
from guard_engineering_inputs import sha


def fixture(root):
    source=root/'source.txt'
    source.write_text('SOFTWARE_FIXTURE_NOT_IFC',encoding='utf-8')
    edge={'id':'e','from':'t','to':'r','length_m':1.,'diameter_m':.2,'polyline_m':[[0.,0.,0.],[1.,0.,0.]],'source_mapping':{'kind':'SOFTWARE_ONLY'}}
    bundle={'edge_id':'e','edge_sha256':edge_fingerprint(edge),'reports':{}}
    for role,scope in ROLES.items():
        data={'scope':scope,'status':'PASS','edge_id':'e','edgeSha256':edge_fingerprint(edge),'unit':'m','method':'SOFTWARE_FIXTURE_ONLY',
            'sourceHashes':{'source.txt':sha(source)},'checks':[{'name':'fixture','status':'PASS','evidence':'SOFTWARE_ONLY'}],
            'clearance_m':.05,'envelopeDiameter_m':.2,'from':'t','to':'r','direction_certified':True,'service_id':'FIXTURE'}
        path=root/(role+'.json')
        path.write_text(json.dumps(data),encoding='utf-8')
        bundle['reports'][role]={'path':path.name,'sha256':sha(path)}
    return edge,bundle


class EdgeEvidenceTests(unittest.TestCase):
    def test_consistent_fixture_only_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            edge,bundle=fixture(root)
            result=authorize(edge,bundle,root)
            self.assertEqual(result['status'],'PASS_EVIDENCE_BINDINGS_ONLY')
            self.assertFalse(result['independent_engineering_certification'])
            self.assertTrue(result['authorized_edge']['authorization_ref'].startswith('EDGE_EVIDENCE_BUNDLE_SHA256:'))

    def test_source_change_invalidates_all_roles(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            edge,bundle=fixture(root)
            (root/'source.txt').write_text('changed',encoding='utf-8')
            result=authorize(edge,bundle,root)
            self.assertEqual(result['status'],'BLOCKED_EDGE_EVIDENCE')
            self.assertIsNone(result['authorized_edge'])

    def test_feature_match_not_service_or_geometry_permission(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            edge,bundle=fixture(root)
            path=root/'service.json'
            data=json.loads(path.read_text(encoding='utf-8'))
            data['status']='NUMERIC_FEATURE_MATCH_ONLY'
            data['direction_certified']=False
            path.write_text(json.dumps(data),encoding='utf-8')
            bundle['reports']['service']['sha256']=sha(path)
            self.assertEqual(authorize(edge,bundle,root)['status'],'BLOCKED_EDGE_EVIDENCE')

    def test_edge_change_missing_evidence_and_length_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            edge,bundle=fixture(root)
            edge['diameter_m']=.3
            self.assertEqual(authorize(edge,bundle,root)['status'],'BLOCKED_EDGE_EVIDENCE')
            edge['length_m']=2.
            self.assertEqual(authorize(edge,{},root)['status'],'BLOCKED_EDGE_EVIDENCE')
            self.assertEqual(authorize({},bundle,root)['status'],'BLOCKED_EDGE_EVIDENCE')

    def test_zero_checks_and_wrong_spatial_diameter_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            edge,bundle=fixture(root)
            path=root/'spatial.json'
            data=json.loads(path.read_text(encoding='utf-8'))
            data['checks']=[]
            data['envelopeDiameter_m']=.1
            path.write_text(json.dumps(data),encoding='utf-8')
            bundle['reports']['spatial']['sha256']=sha(path)
            self.assertEqual(authorize(edge,bundle,root)['status'],'BLOCKED_EDGE_EVIDENCE')


if __name__=='__main__':
    unittest.main()
