import unittest
from types import SimpleNamespace
from audit_alignment_markers import marker_label


class MarkerTests(unittest.TestCase):
    def test_explicit_product_fields_and_missing_values(self):
        self.assertTrue(marker_label(SimpleNamespace(Name='SHARED_Alignment_Cube_(GRA)')))
        self.assertTrue(marker_label(SimpleNamespace(Name='Marker',Description='survey control')))
        self.assertFalse(marker_label(SimpleNamespace(Name='VENT',Description=None)))


if __name__=='__main__':
    unittest.main()
