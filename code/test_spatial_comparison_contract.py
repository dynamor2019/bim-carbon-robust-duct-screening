"""Artificial software metadata fixtures; not BIM engineering results."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from spatial_comparison_contract import bind, fingerprint, selection_record, check_holdout_identity


class ContractTests(unittest.TestCase):
    def packet(self):
        return [
            {'coordinate_unit':'m','qualification':'QUALIFIED_SPATIAL_DOMAIN','evidence_hashes':['fixture-only'], 'admissibility_rule':'synthetic software rule'},
            {'fixed':True,'points':[[0,0,0],[1,0,0]]},
            {'options':['fixture-section'],'envelope_rule':'synthetic software rule'},
            [{'id':'A','geometry':[[0,0,0],[1,0,0]],'section_assignment':['fixture-section']},
             {'id':'B','geometry':[[0,0,0],[0,1,0],[1,0,0]],'section_assignment':['fixture-section']}],
            {'s':{'clearance':'fixture'}}, {'h':{'clearance':'different-fixture'}},
            {'metric':'route_length','unit':'m','definition':'sum geometric lengths'}]

    def test_candidate_order_invariant(self):
        p=self.packet(); original=bind(*p); p[3].reverse()
        self.assertEqual(original,bind(*p))
        self.assertFalse(original['formal_experiment'])
        self.assertFalse(original['scientific_validation'])

    def test_all_frozen_payload_changes_rejected(self):
        p=self.packet(); b=bind(*p); record=selection_record(b,'A')
        self.assertTrue(check_holdout_identity(b,record))
        for position in range(7):
            q=copy.deepcopy(p)
            if position==3:q[3][0]['geometry'][1][0]=2
            elif position in (4,5):q[position][next(iter(q[position]))]['changed_fixture']=True
            else:q[position]['changed_fixture']=True
            changed=bind(*q)
            with self.assertRaises(ValueError):check_holdout_identity(changed,record)

    def test_overlap_and_empty_input_rejected(self):
        p=self.packet();p[5]=p[4]
        with self.assertRaises(ValueError):bind(*p)
        p=self.packet();p[0]={}
        with self.assertRaises(ValueError):bind(*p)
        p=self.packet();p[3]=[]
        with self.assertRaises(ValueError):bind(*p)

    def test_units_and_nonspatial_objective_rejected(self):
        for metric,unit in [('electrical_power','W'),('route_length','kgCO2e')]:
            p=self.packet();p[6].update(metric=metric,unit=unit)
            with self.assertRaises(ValueError):bind(*p)

    def test_duplicate_ids_and_unknown_selection_rejected(self):
        p=self.packet();p[3][1]['id']='A'
        with self.assertRaises(ValueError):bind(*p)
        with self.assertRaises(ValueError):selection_record(bind(*self.packet()),'missing')

    def test_nonfinite_fingerprint_rejected(self):
        with self.assertRaises(ValueError):fingerprint({'value':float('nan')})


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ContractTests))
    project=Path(__file__).resolve().parent.parent
    sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    contract=project/'milestones/reproducibility/spatial-comparison-contract.json'
    report={'artifact_type':'spatial_contract_software_audit','status':'PASS_SOFTWARE_FIXTURES_ONLY' if result.wasSuccessful() else 'FAIL',
        'codeSha256':sha(Path(__file__)),
        'source_files':[{'path':str(project/'code/spatial_comparison_contract.py'),'sha256':sha(project/'code/spatial_comparison_contract.py')}],
        'inputHashes':{'spatial-comparison-contract.json':sha(contract)},
        'command':[sys.executable,'-X','utf8','code/test_spatial_comparison_contract.py'],
        'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'scope':'Artificial metadata and identity fixtures only; not valid geometry or scientific qualification',
        'real_input_status':json.loads(contract.read_text(encoding='utf-8'))['status'],
        'formal_experiment':False}
    out=project/'milestones/reproducibility/spatial-contract-software-audit.json'
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'tests_run':report['tests_run'],'formal_experiment':False}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
