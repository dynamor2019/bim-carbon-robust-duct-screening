"""Synthetic benchmark smoke tests, not experimental findings."""
import copy
import unittest
from run_synthetic_route_size import inputs, generate, evaluate, choose, POLICIES


class SyntheticTests(unittest.TestCase):
    def setUp(self):
        self.r,self.f,self.s,self.length=inputs()
        self.c,self.design,self.holdout=generate(self.f,self.s,self.length)

    def test_geometry_sizes_and_scope(self):
        self.assertEqual(len(self.c),18)
        self.assertEqual(len(self.holdout),12)
        self.assertEqual(self.s['main_analysis']['candidates'],[])
        direct=next(c for c in self.c if c['id']=='R0_D0.160')
        self.assertAlmostEqual(direct['length_m'],self.length)
        self.assertAlmostEqual(next(c for c in self.c if c['route']==1)['length_m'],self.length+1.2)

    def test_clearance_failure_not_zero(self):
        direct=next(c for c in self.c if c['id']=='R0_D0.160')
        value=evaluate(direct,{'flow_m3_s':.05,'clearance_m':.04},self.f,self.length,1,5)
        self.assertFalse(value.feasible);self.assertIsNone(value.cost)

    def test_proxy_formula_for_source_shaped_nominal(self):
        direct=next(c for c in self.c if c['id']=='R0_D0.160')
        self.assertAlmostEqual(evaluate(direct,self.design[1],self.f,self.length,1,5).cost,2)
        self.assertAlmostEqual(evaluate(direct,self.design[1],self.f,self.length,0,5).cost,1)

    def test_all_policies_and_robust_feasibility(self):
        for policy in POLICIES:
            selected=choose(policy,self.c,self.design,self.f,self.length,1,5)
            self.assertIn(selected,{c['id'] for c in self.c})
            if policy in ('robust_joint_minimax','robust_joint_regret','ablation_fixed_shortest','ablation_no_proxy'):
                candidate=next(c for c in self.c if c['id']==selected)
                self.assertTrue(all(evaluate(candidate,s,self.f,self.length,1,5).feasible for s in self.design))

    def test_unknown_diameter_and_duplicate_candidate_budget_rejected(self):
        f=copy.deepcopy(self.f);f['diameters_m']=[.16]
        with self.assertRaises(ValueError):generate(f,self.s,self.length)


if __name__=='__main__':unittest.main()
