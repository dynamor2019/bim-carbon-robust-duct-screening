import unittest
import numpy as np
from mesh_diagnostics import edge_subdivision_audit,nearest_surface
from test_mesh_containment import VERTICES,FACES


class MeshDiagnosticsTests(unittest.TestCase):
    def test_T_junction_closed_after_existing_vertex_bookkeeping(self):
        vertices=np.vstack([VERTICES,[.5,.5,0]])
        faces=np.vstack([[[0,8,1],[8,2,1]],FACES[1:]])
        result=edge_subdivision_audit(vertices,faces)
        self.assertGreater(result['raw_non_two_incident_edges'],0)
        self.assertEqual(result['subdivided_non_two_incident_segments'],0)
        self.assertEqual(result['subdivided_inconsistent_winding'],0)
        self.assertTrue(result['subdivisions'])

    def test_missing_face_is_not_capped(self):
        result=edge_subdivision_audit(VERTICES,FACES[:-1])
        self.assertGreater(result['subdivided_non_two_incident_segments'],0)

    def test_nearest_face_and_corner(self):
        face=nearest_surface([.5,.5,1.02],VERTICES,FACES)
        self.assertAlmostEqual(face['distance_m'],.02)
        self.assertEqual(face['closest_point_m'],[.5,.5,1.])
        corner=nearest_surface([-.1,-.1,-.1],VERTICES,FACES)
        self.assertAlmostEqual(corner['distance_m'],np.sqrt(.03))
        self.assertEqual(corner['closest_point_m'],[0.,0.,0.])


if __name__=='__main__':
    unittest.main()
