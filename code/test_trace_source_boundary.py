"""Verify world-coordinate bbox handling and exact IFC group semantics."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from trace_source_boundary import bbox, group_memberships


class BoundaryTests(unittest.TestCase):
    def test_bbox_uses_world_vertices_once(self):
        shape = SimpleNamespace(geometry=SimpleNamespace(verts=[47.,58.,72., 49.,60.,74.]))
        with patch('trace_source_boundary.ifcopenshell.geom.create_shape', return_value=shape) as create:
            result = bbox(object())
        settings = create.call_args.args[0]
        self.assertTrue(settings.get(settings.USE_WORLD_COORDS))
        self.assertEqual(result['min_m'], [47.,58.,72.])
        self.assertEqual(result['max_m'], [49.,60.,74.])
        self.assertEqual(result['vertex_mean_m'], [48.,59.,73.])

    def test_nonfinite_and_empty_geometry_rejected(self):
        for vertices in ([], [float('nan'),0.,0.]):
            with patch('trace_source_boundary.ifcopenshell.geom.create_shape',
                       return_value=SimpleNamespace(geometry=SimpleNamespace(verts=vertices))):
                with self.assertRaises(ValueError):
                    bbox(object())

    def test_no_assignments_is_not_a_guessed_system(self):
        self.assertEqual(group_memberships(SimpleNamespace(HasAssignments=[])), [])


if __name__ == '__main__':
    unittest.main()
