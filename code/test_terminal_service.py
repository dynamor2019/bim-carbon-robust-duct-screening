"""Name categories and aggregation retain all source records and missing flows."""
import unittest
from audit_terminal_service import product_family,aggregate


class TerminalServiceTests(unittest.TestCase):
    def test_transparent_name_categories(self):
        self.assertEqual(product_family('URH/A-160'),'URH')
        self.assertEqual(product_family('AHD-500-100+PRL/F-500-100-200'),'AHD_PRL')
        self.assertEqual(product_family('unknown exhaust product'),'OTHER_SOURCE_PRODUCT')

    def test_zero_is_valid_and_missing_does_not_become_zero(self):
        rows=[{'product_family':'a','flow_m3_s':0.},{'product_family':'a','flow_m3_s':.2},
              {'product_family':'b','flow_m3_s':None}]
        summary={r['label']:r for r in aggregate(rows,'product_family')}
        self.assertEqual(summary['a']['count'],2)
        self.assertEqual(summary['a']['flow_sum_m3_s'],.2)
        self.assertIsNone(summary['b']['flow_sum_m3_s'])
        self.assertEqual(summary['b']['valid_flow_count'],0)


if __name__=='__main__':
    unittest.main()
