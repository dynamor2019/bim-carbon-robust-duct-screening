"""Check source preservation, units, laminar reference and declared model limits."""

import math
import unittest

from run_source_anchored_screening import extract_segments
from source_anchored_physics import pressure_loss, validate_assumptions


class SourceAnchoredTests(unittest.TestCase):
    """No external model, source project or network dependency."""

    def setUp(self):
        """Provide explicitly modelled values, not mock field evidence."""
        self.parameters = {'density_kg_m3': 1.2, 'kinematic_viscosity_m2_s': 0.000015,
                           'roughness_m': 0.00009, 'efficiency': 0.6,
                           'hours_per_year': 2500, 'grid_kgco2e_kwh': 0.2,
                           'wall_thickness_m': 0.0007, 'steel_density_kg_m3': 7850}

    def test_laminar_matches_poiseuille(self):
        """Verify the pressure equation against an independent analytic limit."""
        q, length, diameter = 0.00001, 2, 0.1
        expected = 128 * 1.2 * 0.000015 * length * q / (math.pi * diameter ** 4)
        result = pressure_loss(q, length, diameter, self.parameters)
        self.assertAlmostEqual(result['pressure_Pa'], expected, places=12)

    def test_transitional_case_is_unknown_not_zero(self):
        """Keep an unresolved flow regime as an explicit null result."""
        flow = 3000 * 0.000015 * math.pi * 0.1 / 4
        self.assertIsNone(pressure_loss(flow, 2, 0.1, self.parameters)['pressure_Pa'])

    def test_units_and_source_zero_are_preserved(self):
        """Never turn an observed zero into invented positive demand."""
        def component(identifier, flow):
            return {'ifc_type': 'IfcDuctSegment', 'ifc_id': identifier, 'guid': str(identifier),
                    'psets': {'FI_Geometria': {'Halkaisija': 160, 'Pituus': 240},
                              'FI_Tekninen': {'Virtaama': flow}}}
        source = {'length_unit_scale_to_m': 0.001, 'sourceSha256': 'a',
                  'sourceSha256_after': 'a', 'components': [component(1, 30), component(2, 0)]}
        included, excluded = extract_segments(source)
        self.assertEqual(included[0]['design_flow_m3_s'], 0.03)
        self.assertEqual(included[0]['length_m'], 0.24)
        self.assertEqual(excluded[0]['source_values'][-1], 0)

    def test_undisclosed_assumption_is_rejected(self):
        """Known-looking values are not evidence without disclosure."""
        register = {name: {'value': value, 'origin': 'ASSUMED', 'rationale': 'test'}
                    for name, value in self.parameters.items()}
        register['efficiency']['origin'] = 'MEASURED'
        with self.assertRaises(ValueError):
            validate_assumptions(register)


if __name__ == '__main__':
    unittest.main()
