import unittest
import numpy as np
from audit_AHU_neighborhood_interfaces import bbox_gap


class NeighborhoodTests(unittest.TestCase):
    def test_gap_overlap_contact_and_diagonal(self):
        low=np.zeros(3)
        high=np.ones(3)
        self.assertEqual(bbox_gap(low,high,low+.5,high+.5),0.)
        self.assertEqual(bbox_gap(low,high,low+[1,0,0],high+[1,0,0]),0.)
        self.assertAlmostEqual(bbox_gap(low,high,low+2,high+2),np.sqrt(3))
        self.assertAlmostEqual(bbox_gap(low,high,low+[1.2,0,0],high+[1.2,0,0]),.2)


if __name__=='__main__':
    unittest.main()
