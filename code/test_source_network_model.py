"""Regression checks for source-first geometry and velocity-dependent local losses."""

import unittest

import networkx as nx

from source_network_model import build_tree, local_pressure, prepare_dimensions


class SourceNetworkTests(unittest.TestCase):
    """Keep missing-value assumptions separate from available source geometry."""

    def test_source_port_dimensions_precede_generated_placeholder(self):
        """A source tee with known large ports must not become a guessed small pipe."""
        component = {'ifc_type': 'IfcDuctFitting', 'psets': {},
                     'features': [{'radii_m': [0.4]}, {'radii_m': [0.25]}]}
        dimensions, assumptions = prepare_dimensions({1: component})
        self.assertEqual(dimensions[1]['diameter'], 0.8)
        self.assertIn('SOURCE', dimensions[1]['origin'])
        self.assertEqual(assumptions, [])

    def test_source_shape_not_overwritten_by_ports(self):
        """Respect known source section values instead of feature-derived reference guesses."""
        component = {'ifc_type': 'IfcDuctFitting', 'psets': {'FI_Geometria': {'Halkaisija': 160}},
                     'features': [{'radii_m': [0.4]}]}
        dimensions, _ = prepare_dimensions({1: component})
        self.assertEqual(dimensions[1]['diameter'], 0.16)

    def test_local_loss_scales_with_changed_velocity(self):
        """At equal flow a larger section must reduce a fixed-coefficient modeled local loss."""
        component = {'ifc_type': 'IfcDamper', 'psets': {'FI_Tekninen':
                     {'Painehäviö': 15, 'Virtausnopeus': 2, 'Virtaama': 30}}}
        loss, _ = local_pressure(component, 0.03, 1, {})
        self.assertEqual(loss, 3.75)

    def test_disconnected_demand_not_silently_discarded(self):
        """A disconnected source terminal invalidates the complete-service candidate."""
        graph = nx.Graph([(1, 2)])
        graph.add_node(3)
        tree, missing = build_tree(graph, 1, 'hop', {2: 0.03, 3: 0.04})
        self.assertIsNone(tree)
        self.assertEqual(missing, [3])


if __name__ == '__main__':
    unittest.main()
