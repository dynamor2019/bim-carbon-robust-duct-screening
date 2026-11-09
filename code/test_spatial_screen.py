"""Spatial bbox screens remain weaker than exact containment; transport fixtures only."""
import unittest
from screen_upper_floor_spaces import bbox_contains,space_role


class SpatialScreenTests(unittest.TestCase):
    def test_xy_overlap_does_not_certify_3D(self):
        self.assertTrue(bbox_contains([.5,.5],[0,0],[1,1]))
        self.assertFalse(bbox_contains([.5,.5,3],[0,0,0],[1,1,2]))

    def test_aggregate_and_accessibility_shapes_flagged(self):
        self.assertEqual(space_role('GFA'),'AGGREGATE_OR_ACCESSIBILITY_GEOMETRY')
        self.assertEqual(space_role('Turning Free Space 1500 mm'),'AGGREGATE_OR_ACCESSIBILITY_GEOMETRY')
        self.assertEqual(space_role('CHASE'),'SHAFT_GEOMETRY')
        self.assertIn('not_service_certification',space_role('SAUNA'))


if __name__=='__main__':
    unittest.main()
