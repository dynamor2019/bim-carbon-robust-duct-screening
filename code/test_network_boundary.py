"""Tests for candidate graph diagnostics, not physical-network validation."""
import unittest
from diagnose_network_boundary import box_gap, components


class NetworkDiagnosticTests(unittest.TestCase):
    def test_isolated_nodes_and_reversed_edges(self):
        result = components({'1','2','3','4'}, {('1','2'),('2','1'),('2','3')})
        self.assertEqual(result, [['1','2','3'], ['4']])

    def test_graph_does_not_create_bridge(self):
        self.assertEqual(components({'a','b','c'}, {('a','b')}), [['a','b'],['c']])

    def test_bbox_overlap_is_only_zero_gap(self):
        row = {f'bbox_{bound}_{a}_m': str(v) for bound,v in [('min',0),('max',1)] for a in 'xyz'}
        self.assertEqual(box_gap(row, {'min_m':[.5,.5,.5], 'max_m':[2,2,2]}),0.)
        self.assertAlmostEqual(box_gap(row, {'min_m':[2,2,1], 'max_m':[3,3,2]}), 2**.5)


if __name__ == '__main__':
    unittest.main()
