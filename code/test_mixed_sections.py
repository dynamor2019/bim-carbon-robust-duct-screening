"""Numerical matching and conditional unit diagnostics; fixtures are not experiment data."""
import unittest
import numpy as np
from screen_mixed_interfaces import rectangle_match
from recover_rectangular_interfaces import rectangle_fit
from audit_flow_units import nominal_area,positive


class MixedSectionTests(unittest.TestCase):
    def setUp(self):
        self.points=np.array([[-1.,-.5,0.],[1.,-.5,0.],[1.,.5,0.],[-1.,.5,0.]])
        self.rectangle=rectangle_fit(self.points)

    def test_corner_order_and_normal_sign_invariance(self):
        other=rectangle_fit(self.points[::-1])
        other['normal_sign_arbitrary']=[-x for x in self.rectangle['normal_sign_arbitrary']]
        self.assertIsNotNone(rectangle_match(self.rectangle,other))

    def test_equal_center_dimensions_do_not_allow_rotation(self):
        rotated=self.points[:,[1,0,2]]
        self.assertIsNone(rectangle_match(self.rectangle,rectangle_fit(rotated)))

    def test_displaced_plane_not_connected(self):
        self.assertIsNone(rectangle_match(self.rectangle,rectangle_fit(self.points+[0,0,2e-5])))

    def test_nominal_mm_area_and_ambiguous_type(self):
        area,kind=nominal_area({'Halkaisija':0.,'Leveys':1400.,'Korkeus':800.})
        self.assertAlmostEqual(area,1.12)
        self.assertEqual(kind,'RECTANGULAR_NOMINAL_MM')
        area,kind=nominal_area({'Halkaisija':200.,'Leveys':0.,'Korkeus':0.})
        self.assertAlmostEqual(area,np.pi*.1**2)
        self.assertIsNone(nominal_area({'Halkaisija':200.,'Leveys':1400.,'Korkeus':800.}))

    def test_missing_zero_and_nonfinite_not_positive(self):
        for value in (None,False,0.,-1.,float('nan'),float('inf')):
            self.assertFalse(positive(value))


if __name__=='__main__':
    unittest.main()
