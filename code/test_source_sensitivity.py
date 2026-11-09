"""Regression tests for uncertainty honesty and fixed-design preservation."""

import math
import unittest

import networkx as nx

from finite_candidate_decisions import Evaluation
from source_sensitivity import fixed_candidates, policy_evidence, variant_inputs, verify_baseline
from source_sensitivity_benchmarks import reference_loss
from source_sensitivity_protocol import MISSING_IDS, make_protocol


class SensitivityTests(unittest.TestCase):
    """Test selection separation, immutability and numerical reference checks."""

    def test_sampling_is_deterministic_and_bounded(self):
        """All factors remain inside frozen bounds, with interactions represented."""
        first, second = make_protocol(), make_protocol()
        self.assertEqual(first['variants'], second['variants'])
        self.assertEqual(len(first['variants']), 89)
        for variant in first['variants']:
            for factor in first['factors']:
                self.assertLessEqual(factor['low'], variant['factors'][factor['name']])
                self.assertGreaterEqual(factor['high'], variant['factors'][factor['name']])

    def test_dimensions_do_not_mutate_known_inputs(self):
        """Only actual unresolved dimensions can be substituted."""
        dimension = dict(origin='ASSUMED_MISSING_COMPONENT_DIMENSION', diameter=0.16, area=0.02, perimeter=0.5)
        dimensions = {MISSING_IDS[0]: dimension}
        register = {'parameters': {'missing_local_loss_coefficients': {'fitting': 2}}}
        updated, sizes = variant_inputs(register, dimensions,
                                        {f'dimension_{MISSING_IDS[0]}': 0.12, 'local_loss_multiplier': 0.5})
        self.assertEqual(dimension['diameter'], 0.16)
        self.assertEqual(register['parameters']['missing_local_loss_coefficients']['fitting'], 2)
        self.assertEqual(updated['parameters']['missing_local_loss_coefficients']['fitting'], 1)
        self.assertEqual(sizes[MISSING_IDS[0]]['diameter'], 0.12)
        dimension['origin'] = 'SOURCE_NOMINAL_CIRCULAR_DIMENSION'
        with self.assertRaises(ValueError):
            variant_inputs(register, dimensions, {f'dimension_{MISSING_IDS[0]}': 0.12})

    def test_designed_interventions_stay_fixed(self):
        """Uncertainty in source geometry must not resize installed counterfactuals."""
        a, b = MISSING_IDS[:2]
        tree = nx.DiGraph([(a, b)])
        candidates = {'c': {'tree': tree, 'sizes': {
            a: {'origin': 'ASSUMED_MISSING_COMPONENT_DIMENSION', 'diameter': 0.16},
            b: {'origin': 'MODELLED_COUNTERFACTUAL_DESIGN', 'diameter': 0.20}}}}
        updated = fixed_candidates(candidates, {a: {'diameter': 0.12}, b: {'diameter': 0.12}})
        self.assertIs(updated['c']['tree'], tree)
        self.assertEqual(updated['c']['sizes'][a]['diameter'], 0.12)
        self.assertEqual(updated['c']['sizes'][b]['diameter'], 0.20)
        self.assertEqual(candidates['c']['sizes'][a]['diameter'], 0.16)

    def test_held_out_cannot_choose_policy(self):
        """An attractive held-out alternative cannot leak into design selection."""
        register = dict(design_demand_multipliers=[1.0], held_out_demand_multipliers=[1.1],
                        held_out_grid_factors=[0.2], parameters={'grid_kgco2e_kwh': 0.2})
        matrices = {'a': {'D0': Evaluation(True, 1), 'H0_0': Evaluation(False, None)},
                    'b': {'D0': Evaluation(True, 2), 'H0_0': Evaluation(True, 0)}}
        policies = {mode: {'selected': 'a'} for mode in ('deterministic', 'minimax', 'minimax_regret')}
        evidence = policy_evidence(matrices, register, policies)
        self.assertEqual(evidence['selections']['minimax_regret']['selected'], 'a')
        self.assertIsNone(evidence['frozen_label_assessment']['minimax_regret']['scenarios'][0]['regret'])
        self.assertEqual(evidence['frozen_label_assessment']['minimax_regret']['failure_count'], 1)

    def test_reference_laminar_and_unknown(self):
        """The benchmark is analytic for laminar flow and preserves transition null."""
        parameters = dict(density_kg_m3=1.2, kinematic_viscosity_m2_s=0.000015, roughness_m=0.00009)
        flow = 1000 * parameters['kinematic_viscosity_m2_s'] * math.pi * 0.1 / 4
        self.assertAlmostEqual(reference_loss(flow, 10, 0.1, parameters), 0.0864)
        self.assertIsNone(reference_loss(flow * 3, 10, 0.1, parameters))

    def test_changed_baseline_is_rejected(self):
        """Fail closed instead of presenting changed outputs as the original."""
        baseline = {'records': [dict(candidate_id='a', scenario_id='D0', objective=None)]}
        with self.assertRaises(ValueError):
            verify_baseline([dict(candidate_id='a', scenario_id='D0', objective=1)], baseline)


if __name__ == '__main__':
    unittest.main()
