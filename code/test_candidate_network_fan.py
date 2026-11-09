"""Coupled arithmetic fixtures only; no case fan/resistance data or flow tolerance."""
import math
import unittest
from candidate_network_fan import direct_roots,evaluate


def edge(key,a,b):
    return {'id':key,'from':a,'to':b,'length_m':1.,'diameter_m':.2,'connection_authorized':True,'spatial_authorized':True,'authorization_ref':'SOFTWARE_ONLY'}


def fixture():
    model={'boundary':'COMMON_LEAF_PRESSURE','resistance_law':'FIXED_QUADRATIC','controls':'NONE','source_ref':'SOFTWARE_ONLY'}
    conditions={'density_kg_m3':1.,'speed_rpm':1000.,'installation_category':'SOFTWARE_ONLY'}
    fan={'pressure_basis':'fan_total','power_basis':'electrical_input','source_ref':'SOFTWARE_ONLY','conditions':conditions,
        'stable_flow_interval_m3_s':[.1,5.],
        'points':[{'flow_m3_s':.1,'pressure_Pa':4.,'electrical_power_W':10.},{'flow_m3_s':5.,'pressure_Pa':4.,'electrical_power_W':20.}]}
    bounds={t:{'minimum_m3_s':1.4,'maximum_m3_s':1.6,'source_ref':'SOFTWARE_ONLY'} for t in ('a','b')}
    return model,conditions,fan,bounds


class NetworkFanTests(unittest.TestCase):
    def test_exact_quadratic_intersection(self):
        points=[{'flow_m3_s':0.,'pressure_Pa':10.},{'flow_m3_s':10.,'pressure_Pa':0.}]
        roots=direct_roots(points,1.,[0.,10.],1e-10,1e-9)
        self.assertEqual(len(roots),1)
        self.assertAlmostEqual(roots[0]['flow_m3_s'],(-1+math.sqrt(41))/2)
        self.assertTrue(roots[0]['negative_net_slope_all_segments'])

    def test_intersection_total_flow_does_not_certify_terminal_demands(self):
        model,conditions,fan,bounds=fixture()
        row=evaluate(['a','b','r'],[edge('a','a','r'),edge('b','b','r')],'r',{'a':1.,'b':4.},{'a':0.,'b':0.},model,fan,conditions,'fan_total',bounds,1e-10,1e-9)
        self.assertEqual(row['status'],'FAIL_RESTRICTED_MODEL_DEMAND_OR_SLOPE')
        candidate=row['operating_candidates'][0]
        self.assertAlmostEqual(candidate['network']['total_flow_m3_s'],3.)
        self.assertEqual([r['status'] for r in candidate['terminal_checks']],['OVERSUPPLY','UNDERSUPPLY'])
        self.assertIsNone(row['complete_engineering_feasibility'])

    def test_restricted_matching_bounds_only_pass(self):
        model,conditions,fan,bounds=fixture()
        bounds['a'].update(minimum_m3_s=1.99,maximum_m3_s=2.01)
        bounds['b'].update(minimum_m3_s=.99,maximum_m3_s=1.01)
        row=evaluate(['a','b','r'],[edge('a','a','r'),edge('b','b','r')],'r',{'a':1.,'b':4.},{'a':0.,'b':0.},model,fan,conditions,'fan_total',bounds,1e-10,1e-9)
        self.assertEqual(row['status'],'PASS_RESTRICTED_MODEL_DEMAND_CHECK_ONLY')
        self.assertFalse(row['actual_operation_certified'])

    def test_multiple_supported_roots_retained(self):
        points=[{'flow_m3_s':0.,'pressure_Pa':.1},{'flow_m3_s':1.,'pressure_Pa':.1},{'flow_m3_s':2.,'pressure_Pa':5.},{'flow_m3_s':3.,'pressure_Pa':5.}]
        self.assertEqual(len(direct_roots(points,1.,[0.,3.],1e-10,1e-9)),3)

    def test_missing_bound_and_outside_stability_rejected(self):
        model,conditions,fan,bounds=fixture()
        with self.assertRaises(ValueError):
            evaluate(['a','b','r'],[edge('a','a','r'),edge('b','b','r')],'r',{'a':1.,'b':4.},{'a':0.,'b':0.},model,fan,conditions,'fan_total',{},1e-10,1e-9)
        self.assertEqual(direct_roots(fan['points'],10000.,fan['stable_flow_interval_m3_s'],1e-10,1e-9),[])


if __name__=='__main__':
    unittest.main()
