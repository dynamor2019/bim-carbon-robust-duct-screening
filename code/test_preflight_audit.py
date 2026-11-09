"""Tests for audit units, missingness and source-line provenance."""
import math
import tempfile
import unittest
from pathlib import Path
from preflight_audit import flow_check, load_csv, number, section_area


class AuditTests(unittest.TestCase):
    def test_missing_and_zero_are_distinct(self):
        self.assertIsNone(number(''))
        self.assertEqual(number('0'), 0)
        for value in ('nan', 'inf', '-inf'):
            with self.assertRaises(ValueError):
                number(value)

    def test_circular_and_rectangular_conservation(self):
        circle = {'diameter_m': '.2', 'flow_rate_raw': str(math.pi * .2**2 / 4 * 3 * 1000), 'velocity_raw': '3'}
        rectangle = {'width_m': '.4', 'height_m': '.2', 'flow_rate_raw': '240', 'velocity_raw': '3'}
        for row in (circle, rectangle):
            self.assertLess(flow_check(row)['relative_error'], 1e-12)
        self.assertAlmostEqual(section_area(rectangle)[0], .08)

    def test_ambiguous_shape_and_zero_flow_not_imputed(self):
        self.assertEqual(section_area({'diameter_m': '.2', 'width_m': '.2', 'height_m': '.2'})[1], 'ambiguous')
        self.assertEqual(flow_check({'diameter_m': '.2', 'flow_rate_raw': '0', 'velocity_raw': '2'})['status'], 'nonpositive')
        self.assertEqual(flow_check({'diameter_m': '.2', 'velocity_raw': '2'})['status'], 'missing_or_ambiguous')

    def test_multiline_csv_source_locations(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'source.csv'
            path.write_text('id,text\n1,"first\nsecond"\n2,third\n', encoding='utf-8', newline='')
            rows = load_csv(path)
            self.assertEqual([r['_source_line'] for r in rows], [2, 4])
            self.assertEqual(rows[0]['text'], 'first\nsecond')


if __name__ == '__main__':
    unittest.main()
