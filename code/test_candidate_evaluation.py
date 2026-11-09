"""Integration software fixture only; no actual service network or fan selection."""
import copy
import tempfile
import unittest
from pathlib import Path
from evaluate_candidate_design import evaluate_case,evaluate_authorized_arithmetic


def case_fixture():
    return {'nodes':['t','r'],'root':'r','terminal_demands_m3_s':{'t':.1},'maximum_velocity_m_s':10.,
        'edges':[{'id':'e','from':'t','to':'r','length_m':1.,'diameter_m':.2,'connection_authorized':True,'spatial_authorized':True,'authorization_ref':'SOFTWARE_ONLY'}],
        'edge_physics':{'e':{'density_kg_m3':1.,'darcy_factor':.02,'local_losses':[],'friction_ref':'SOFTWARE_ONLY'}},
        'terminal_boundary_losses_Pa':{'t':0.},'root_boundary_loss_Pa':0.,'pressure_basis':'fan_total',
        'fan_conditions':{'density_kg_m3':1.,'speed_rpm':1000.,'installation_category':'FIXTURE'},
        'fan_curve':{'pressure_basis':'fan_total','power_basis':'electrical_input','source_ref':'SOFTWARE_ONLY',
            'conditions':{'density_kg_m3':1.,'speed_rpm':1000.,'installation_category':'FIXTURE'},'stable_flow_interval_m3_s':[.05,.2],
            'points':[{'flow_m3_s':.05,'pressure_Pa':100.,'electrical_power_W':100.},{'flow_m3_s':.2,'pressure_Pa':50.,'electrical_power_W':200.}]}}


class CandidateIntegrationTests(unittest.TestCase):
    def test_blocked_gate_prevents_any_physics(self):
        with tempfile.TemporaryDirectory() as folder:
            result=evaluate_case(case_fixture(),{}, {},Path(folder),'a'*64,'b'*64)
            self.assertEqual(result['status'],'BLOCKED_ENGINEERING_INPUT_GATE')
            self.assertFalse(result['physics_executed'])
            self.assertEqual(result['stages'],[])

    def test_composed_arithmetic_cannot_claim_engineering_feasible(self):
        result=evaluate_authorized_arithmetic(case_fixture())
        self.assertEqual(result['status'],'BLOCKED_OPERATING_POINT_AND_BALANCE_UNCERTIFIED')
        self.assertEqual(len(result['stages']),4)
        self.assertIsNone(result['engineering_feasible'])
        self.assertIsNone(result['objective_cost'])
        self.assertFalse(result['carbon_ledger_executed'])
        self.assertAlmostEqual(result['stages'][0]['result']['terminal_total_m3_s'],.1)

    def test_velocity_failure_stops_before_fan(self):
        case=case_fixture()
        case['maximum_velocity_m_s']=.01
        result=evaluate_authorized_arithmetic(case)
        self.assertEqual(result['status'],'FAIL_CANDIDATE_VELOCITY')
        self.assertEqual(len(result['stages']),1)

    def test_missing_boundary_and_wrong_pressure_keep_partial_diagnostics(self):
        case=case_fixture()
        case['terminal_boundary_losses_Pa']={}
        result=evaluate_authorized_arithmetic(case)
        self.assertEqual(result['status'],'BLOCKED_INVALID_OR_MISSING_STAGE_INPUT')
        self.assertEqual(len(result['stages']),2)
        case=case_fixture()
        case['pressure_basis']='fan_static'
        result=evaluate_authorized_arithmetic(case)
        self.assertEqual(result['status'],'BLOCKED_INVALID_OR_MISSING_STAGE_INPUT')
        self.assertEqual(len(result['stages']),3)


if __name__=='__main__':
    unittest.main()
