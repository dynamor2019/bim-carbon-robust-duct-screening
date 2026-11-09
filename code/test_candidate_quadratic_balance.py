"""Analytical resistance fixtures only; no real network coefficients."""
import unittest
from candidate_quadratic_balance import solve,system_points


def edge(key,a,b):
    return {'id':key,'from':a,'to':b,'length_m':1.,'diameter_m':.2,'spatial_authorized':True,'connection_authorized':True,'authorization_ref':'SOFTWARE_ONLY'}

MODEL={'boundary':'COMMON_LEAF_PRESSURE','resistance_law':'FIXED_QUADRATIC','controls':'NONE','source_ref':'SOFTWARE_ONLY'}


class QuadraticBalanceTests(unittest.TestCase):
    def test_series_analytic(self):
        row=solve(['t','r'],[edge('e','t','r')],'r',{'t':2.},{'e':3.},2.,MODEL)
        self.assertAlmostEqual(row['equivalent_resistance_Pa_per_m3_s_squared'],5.)
        self.assertAlmostEqual(row['system_pressure_Pa'],20.)
        self.assertAlmostEqual(row['terminal_flow_m3_s']['t'],2.)

    def test_parallel_unequal_branches_not_equal_target_allocation(self):
        row=solve(['a','b','r'],[edge('a','a','r'),edge('b','b','r')],'r',{'a':1.,'b':4.},{'a':0.,'b':0.},3.,MODEL)
        self.assertAlmostEqual(row['terminal_flow_m3_s']['a'],2.)
        self.assertAlmostEqual(row['terminal_flow_m3_s']['b'],1.)
        self.assertAlmostEqual(row['system_pressure_Pa'],4.)
        self.assertTrue(all(abs(p['root_pressure_residual_Pa'])<1e-9 for p in row['paths']))
        self.assertIsNone(row['design_demands_satisfied'])

    def test_shared_trunk_and_quadratic_curve(self):
        row=solve(['a','b','j','r'],[edge('a','a','j'),edge('b','b','j'),edge('c','j','r')],'r',{'a':1.,'b':1.},{'a':0.,'b':0.,'c':1.},2.,MODEL)
        self.assertAlmostEqual(row['equivalent_resistance_Pa_per_m3_s_squared'],1.25)
        self.assertAlmostEqual(row['edge_flow_m3_s']['c'],2.)
        self.assertEqual(system_points(1.25,[0.,1.,2.]),[{'flow_m3_s':0.,'pressure_Pa':0.},{'flow_m3_s':1.,'pressure_Pa':1.25},{'flow_m3_s':2.,'pressure_Pa':5.}])

    def test_zero_flow_and_unsupported_models(self):
        row=solve(['t','r'],[edge('e','t','r')],'r',{'t':2.},{'e':3.},0.,MODEL)
        self.assertEqual(row['system_pressure_Pa'],0.)
        for changed in ({'controls':'VAV'},{'boundary':'UNEQUAL_LEAF_PRESSURES'},{'resistance_law':'VARIABLE_K'}):
            with self.assertRaises(ValueError):
                solve(['t','r'],[edge('e','t','r')],'r',{'t':2.},{'e':3.},1.,dict(MODEL,**changed))

    def test_missing_signed_singular_and_bad_grid_rejected(self):
        for terminal,loss in (({'t':0.},{'e':3.}),({'t':2.},{'e':-1.}),({'t':2.},{})):
            with self.assertRaises(ValueError):
                solve(['t','r'],[edge('e','t','r')],'r',terminal,loss,1.,MODEL)
        with self.assertRaises(ValueError):
            system_points(1.,[1.,0.])


if __name__=='__main__':
    unittest.main()
