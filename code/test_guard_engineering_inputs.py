import copy
import math
import tempfile
import unittest
from pathlib import Path
from guard_engineering_inputs import SPECS,finite_tree,inspect,local_evidence,scenario_ids,sha


class EngineeringIntakeTests(unittest.TestCase):
    def test_nested_nonfinite_values_and_id_leakage(self):
        self.assertFalse(finite_tree({'curve':[1.,float('nan')]}))
        self.assertTrue(finite_tree({'curve':[1.,2.]}))
        self.assertIsNone(scenario_ids([{'id':'x'},{'id':'x'}]))
        self.assertIsNone(scenario_ids([{'id':''}]))
        self.assertEqual(scenario_ids([{'id':'x'},{'id':'y'}]),['x','y'])

    def test_stale_hash_and_outside_path_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            source=root/'source.txt'
            source.write_text('software fixture only',encoding='utf-8')
            record={'path':'source.txt','sha256':sha(source)}
            self.assertTrue(local_evidence(record,root))
            source.write_text('changed fixture',encoding='utf-8')
            self.assertFalse(local_evidence(record,root))
            self.assertFalse(local_evidence({'path':'../external.txt','sha256':'a'*64},root))

    def test_null_input_and_tag_only_cannot_pass(self):
        packet={'schema_version':1,'protocol_state':'REFROZEN','parameters':{name:{'unit':unit,'value':None,'evidence':[]} for name,(unit,kind) in SPECS.items()}}
        with tempfile.TemporaryDirectory() as folder:
            checks=inspect(packet,{},Path(folder),'a'*64,'b'*64)
            by_name={c['name']:c['status'] for c in checks}
            for name in SPECS:
                self.assertEqual(by_name[name],'BLOCKED')
            self.assertEqual(by_name['input_validation_binding'],'BLOCKED')
            self.assertEqual(by_name['distinct_input_validators'],'BLOCKED')
            checks=inspect([],[],Path(folder),'a'*64,'b'*64)
            self.assertTrue(any(c['status']=='BLOCKED' for c in checks))

    def test_wrong_units_boolean_nan_and_overlap_block(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            source=root/'fixture.txt'
            source.write_text('not engineering data',encoding='utf-8')
            evidence=[{'path':'fixture.txt','sha256':sha(source)}]
            packet={'schema_version':1,'protocol_state':'REFROZEN','parameters':{name:{'unit':unit,'value':None,'evidence':evidence} for name,(unit,kind) in SPECS.items()}}
            packet['parameters']['velocity_limit']['value']=True
            packet['parameters']['analysis_horizon']['value']=float('inf')
            packet['parameters']['terminal_demands'].update(value=[{'id':'a','q':1.}],unit='m3/h')
            packet['parameters']['design_scenarios']['value']=[{'id':'same'}]
            packet['parameters']['held_out_scenarios']['value']=[{'id':'same'}]
            checks=inspect(packet,{},root,'a'*64,'b'*64)
            blocked={c['name'] for c in checks if c['status']=='BLOCKED'}
            self.assertTrue({'velocity_limit','analysis_horizon','terminal_demands','held_out_ids'}<=blocked)


if __name__=='__main__':
    unittest.main()
