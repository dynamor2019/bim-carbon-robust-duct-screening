import unittest
from audit_duct_size_specification import band

class BandTests(unittest.TestCase):
    def test_endpoints(self):
        self.assertEqual([band(x,'CIRCULAR') for x in (100,315,400,800,1000,1250)],[.5,.5,.7,.7,.9,.9])
    def test_gaps_are_not_filled(self):
        for x in (63,355,900,1400): self.assertIsNone(band(x,'CIRCULAR'))
        for x in (280,900): self.assertIsNone(band(x,'RECTANGULAR'))
    def test_longest_side_and_invalid(self):
        self.assertEqual(band(1600,'RECTANGULAR'),.9)
        for x in (None,0,-1,float('nan'),True): self.assertIsNone(band(x,'CIRCULAR'))
        self.assertIsNone(band(160,'UNKNOWN'))

if __name__=='__main__': unittest.main()
