"""Guard diagnostic missing/nonfinite handling; no engineering fixture results."""
import unittest
from audit_pipe_geometry_losses import numeric


class PipeLossDiagnosticTests(unittest.TestCase):
    def test_missing_nonfinite_and_boolean_not_numbers(self):
        for value in (None,'',float('nan'),float('inf'),True):
            self.assertIsNone(numeric(value))

    def test_zero_and_negative_remain_observed(self):
        self.assertEqual(numeric(0),0.)
        self.assertEqual(numeric(-.1),-.1)
        self.assertEqual(numeric(.215),.215)


if __name__=='__main__':
    unittest.main()
