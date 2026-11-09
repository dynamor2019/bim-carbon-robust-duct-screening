import unittest
from audit_AHU_rim_offsets import offsets


class RimOffsetTests(unittest.TestCase):
    def test_gap_is_retained_and_wrong_radius_rejected(self):
        a={'center_m':[0.,0.,0.],'normal_sign_arbitrary':[0.,0.,1.],'radii_m':[.2]}
        b=dict(a,center_m=[0.,0.,.05])
        rows=offsets([a],[b])
        self.assertAlmostEqual(rows[0]['center_gap_m'],.05)
        self.assertFalse(rows[0]['strict_numerical_center_match'])
        self.assertEqual(offsets([a],[dict(b,radii_m=[.25])]),[])
        self.assertTrue(offsets([a],[a])[0]['strict_numerical_center_match'])


if __name__=='__main__':
    unittest.main()
