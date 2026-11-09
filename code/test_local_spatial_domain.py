"""Tests of local source-candidate generation; artificial metadata, not BIM results."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from generate_local_spatial_domain import freeze_local, local_candidate
from spatial_comparison_contract import bind


class DomainTests(unittest.TestCase):
    def packet(self):
        c={'ifc_id':1,'guid':'fixture','ifc_type':'IfcDuctSegment','method':'source_circular_extrusion',
            'bbox_min_m':[-.1,-.1,0],'bbox_max_m':[.1,.1,2],'mesh_path':'fixture','mesh_sha256':'fixture',
            'axes':[{'end_a_m':[0,0,0],'end_b_m':[0,0,2],'source_outer_radius_m':.1}]}
        return [{'model_id':'fixture','sourceSha256':'fixture','components':[c]},
            {'status':'PASS_CANDIDATE_INVENTORIES_ONLY'},
            {'invalid_space_count':1,'models':[{'source':'fixture','spaces':[{'ifc_id':10,'status':'INVALID'}]}]},
            {'status':'LOCAL_MARKER_EVIDENCE_ONLY'},{'non_reportable':['energy_kwh','total_carbon_kgco2e']}]

    def test_unknowns_never_main_analysis(self):
        r=freeze_local(*self.packet())
        self.assertFalse(r['main_analysis']['ready_for_contract_binding'])
        self.assertEqual(r['main_analysis']['candidates'],[])
        self.assertTrue(all(p['engineering_status']=='UNKNOWN' for p in r['endpoints']))
        self.assertEqual(len(r['architecture_quarantine']),1)
        self.assertFalse(r['formal_experiment'])
        with self.assertRaises(ValueError):
            bind(r['main_analysis']['domain'],{}, {},[],{}, {},{})

    def test_nonpositive_nan_or_no_axis_not_fabricated(self):
        for value in (0,float('nan')):
            p=self.packet();p[0]['components'][0]['axes'][0]['source_outer_radius_m']=value
            with self.assertRaises(ValueError):local_candidate(p[0])
        p=self.packet();p[0]['components'][0]['axes']=[]
        with self.assertRaises(ValueError):local_candidate(p[0])

    def test_selection_and_tie_independent_of_input_order(self):
        p=self.packet();c=copy.deepcopy(p[0]['components'][0]);c['ifc_id']=2
        p[0]['components'].insert(0,c)
        self.assertEqual(local_candidate(p[0])[0]['ifc_id'],1)
        p[0]['components'][0]['axes'][0]['end_b_m']=[0,0,3]
        self.assertEqual(local_candidate(p[0])[0]['ifc_id'],2)

    def test_bbox_overlap_not_promoted_to_clash(self):
        p=self.packet();p[0]['components'].append({'ifc_id':2,'ifc_type':'IfcDuctFitting',
            'bbox_min_m':[0,0,1],'bbox_max_m':[1,1,3]})
        r=freeze_local(*p)
        self.assertEqual(len(r['obstacle_candidates']),1)
        self.assertEqual(r['obstacle_candidates'][0]['status'],'BBOX_INTERSECTION_CANDIDATE_NOT_SOLID_CLASH')

    def test_source_size_not_qualified_catalogue(self):
        r=freeze_local(*self.packet())
        self.assertEqual(r['sections'][0]['outer_diameter_m'],.2)
        self.assertEqual(r['sections'][0]['alternative_sizes'],[])
        self.assertEqual(r['roi']['padding_m'],0)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(DomainTests))
    p=Path(__file__).resolve().parent.parent;r=p/'milestones/reproducibility'
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    report={'artifact_type':'local_spatial_domain_generator_software_audit',
        'status':'PASS_SOFTWARE_FIXTURES_ONLY' if result.wasSuccessful() else 'FAIL',
        'codeSha256':sha(Path(__file__)),
        'source_files':[{'path':str(p/'code'/name),'sha256':sha(p/'code'/name)} for name in
            ['generate_local_spatial_domain.py','spatial_comparison_contract.py']],
        'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'command':[sys.executable,'-X','utf8','code/test_local_spatial_domain.py'],
        'scope':'Artificial generator, exclusion and contract interoperability fixtures only',
        'formal_experiment':False}
    (r/'local-spatial-domain-software-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'tests_run':report['tests_run']}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
