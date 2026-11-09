"""EPD parser guards; tests are source-token fixtures, not experiment factors."""
import unittest
from qualify_halton_epd import cell


class EPDCellTests(unittest.TestCase):
    def test_not_declared_not_relevant_and_zero_distinct(self):
        self.assertIsNone(cell('MND')['value'])
        self.assertEqual(cell('MND')['state'],'NOT_DECLARED')
        self.assertEqual(cell('MNR')['state'],'NOT_RELEVANT')
        self.assertEqual(cell('0,00E+00')['value'],0.)
        self.assertEqual(cell('0,00E+00')['state'],'DECLARED')

    def test_negative_and_printed_precision_preserved(self):
        parsed=cell('−3,06E+00')
        self.assertEqual(parsed['value'],-3.06)
        self.assertEqual(parsed['rounding_half_unit'],.005)

    def test_unknown_or_nonfinite_token_rejected(self):
        for token in ('NaN','1.77','unknown',''):
            with self.assertRaises(ValueError):
                cell(token)


if __name__=='__main__':
    unittest.main()
