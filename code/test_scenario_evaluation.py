import unittest
from scenario_evaluation import run_scenarios


class ScenarioTests(unittest.TestCase):
    def test_complete_pass_but_selector_requires_engineering_flag(self):
        scenarios=[{'id':'nominal','input_sha256':'a'*64},{'id':'heldout','input_sha256':'b'*64}]
        def run(cid,s):
            return {'status':'PASS_RESTRICTED_MODEL_DEMAND_CHECK_ONLY','engineering_feasible':True,'engineering_validation':'VERIFIED_FOR_CURRENT_INPUT','objective_cost':1.,'input_sha256':s['input_sha256']}
        result=run_scenarios(['A','B'],scenarios,run)
        self.assertTrue(result['selection_allowed'])
        self.assertTrue(result['all_candidates_all_scenarios_complete'])
        self.assertEqual(result['results']['A']['nominal'].cost,1.)

    def test_hash_mismatch_blocks_and_never_becomes_zero_cost(self):
        scenarios=[{'id':'s','input_sha256':'a'*64}]
        result=run_scenarios(['A'],scenarios,lambda c,s:{'status':'PASS_RESTRICTED_MODEL_DEMAND_CHECK_ONLY','engineering_feasible':True,'engineering_validation':'VERIFIED_FOR_CURRENT_INPUT','objective_cost':0.,'input_sha256':'b'*64})
        self.assertFalse(result['selection_allowed'])
        self.assertFalse(result['results']['A']['s'].feasible)
        self.assertIsNone(result['results']['A']['s'].cost)
        self.assertEqual(result['records'][0]['status'],'BLOCKED_INPUT_HASH_MISMATCH')

    def test_infeasible_is_retained_and_all_ids_required(self):
        scenarios=[{'id':'s1','input_sha256':'a'*64},{'id':'s2','input_sha256':'b'*64}]
        def run(c,s):
            return {'status':'FAIL_INSUFFICIENT_PRESSURE','engineering_feasible':None,'objective_cost':None,'input_sha256':s['input_sha256']}
        result=run_scenarios(['A'],scenarios,run)
        self.assertFalse(result['selection_allowed'])
        self.assertEqual(len(result['records']),2)
        with self.assertRaises(ValueError):
            run_scenarios(['A'],[{'id':'s1','input_sha256':'a'*64},{'id':'s1','input_sha256':'b'*64}],run)

    def test_nonfinite_feasible_objective_rejected(self):
        scenarios=[{'id':'s','input_sha256':'a'*64}]
        with self.assertRaises(ValueError):
            run_scenarios(['A'],scenarios,lambda c,s:{'status':'PASS_RESTRICTED_MODEL_DEMAND_CHECK_ONLY','engineering_feasible':True,'engineering_validation':'VERIFIED_FOR_CURRENT_INPUT','objective_cost':float('nan'),'input_sha256':'a'*64})


    def test_verified_infeasible_does_not_block_other_candidate_selection(self):
        scenarios=[{'id':'s','input_sha256':'a'*64}]
        def run(c,s):
            return {'status':'VALIDATED_RESULT','engineering_validation':'VERIFIED_FOR_CURRENT_INPUT','engineering_feasible':c=='B',
                'objective_cost':2. if c=='B' else None,'input_sha256':s['input_sha256']}
        result=run_scenarios(['A','B'],scenarios,run)
        self.assertTrue(result['selection_allowed'])
        self.assertFalse(result['results']['A']['s'].feasible)
        self.assertEqual(result['records'][0]['status'],'VERIFIED_INFEASIBLE')

    def test_runner_cannot_mutate_frozen_record(self):
        scenarios=[{'id':'s','input_sha256':'a'*64,'payload':{'x':1}}]
        def run(c,s):
            s['payload']['x']=9
            return {'status':'BLOCKED','input_sha256':s['input_sha256']}
        result=run_scenarios(['A'],scenarios,run)
        self.assertEqual(scenarios[0]['payload']['x'],1)
        self.assertFalse(result['selection_allowed'])

    def test_restricted_pass_without_validation_is_not_selectable(self):
        scenarios=[{'id':'s','input_sha256':'a'*64}]
        result=run_scenarios(['A'],scenarios,lambda c,s:{'status':'PASS_RESTRICTED_MODEL_DEMAND_CHECK_ONLY','engineering_feasible':True,'objective_cost':1.,'input_sha256':s['input_sha256']})
        self.assertFalse(result['selection_allowed'])


if __name__=='__main__':
    unittest.main()
