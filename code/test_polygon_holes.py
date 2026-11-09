import unittest
import numpy as np
from polygon_holes import hole_audit,point_in_ring

OUTER=np.array([[0,0,0],[4,0,0],[4,4,0],[0,4,0]],float)
HOLE=np.array([[1,1,0],[1,2,0],[2,2,0],[2,1,0]],float)


class HoleTests(unittest.TestCase):
    def test_valid_net_area_and_translation(self):
        for shift in (np.zeros(3),np.array([50,70,74])):
            report=hole_audit(OUTER+shift,[HOLE+shift])
            self.assertEqual(report['status'],'PASS_HOLE_RING_SCOPE')
            self.assertAlmostEqual(report['net_area_m2'],15.)
        self.assertEqual(point_in_ring([0,1],OUTER[:,:2]),'BOUNDARY')

    def test_outside_touching_and_noncoplanar(self):
        self.assertEqual(hole_audit(OUTER,[HOLE+[4,0,0]])['status'],'INVALID_HOLE_DOMAIN')
        self.assertEqual(hole_audit(OUTER,[HOLE+[-1,0,0]])['status'],'INVALID_HOLE_DOMAIN')
        self.assertEqual(hole_audit(OUTER,[HOLE+[0,0,.01]])['status'],'INVALID_HOLE_DOMAIN')

    def test_nested_and_intersecting_holes_rejected(self):
        self.assertEqual(hole_audit(OUTER,[HOLE,HOLE+[.5,0,0]])['status'],'INVALID_HOLE_DOMAIN')
        nested=(HOLE-[1.5,1.5,0])*.5+[1.5,1.5,0]
        self.assertEqual(hole_audit(OUTER,[HOLE,nested])['status'],'INVALID_HOLE_DOMAIN')


if __name__=='__main__':
    unittest.main()
