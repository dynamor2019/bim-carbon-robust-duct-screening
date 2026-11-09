import unittest
import numpy as np
from mesh_containment import mesh_integrity,classify_point

VERTICES=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]],float)
FACES=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]])


class ContainmentTests(unittest.TestCase):
    def test_closed_cube_inside_outside_boundary(self):
        self.assertEqual(mesh_integrity(VERTICES,FACES)['status'],'EDGE_CLOSED_ORIENTED')
        self.assertEqual(classify_point([.5,.5,.5],VERTICES,FACES)['status'],'INSIDE_NUMERICAL')
        self.assertEqual(classify_point([1.5,.5,.5],VERTICES,FACES)['status'],'OUTSIDE_NUMERICAL')
        self.assertEqual(classify_point([1,.5,.5],VERTICES,FACES)['status'],'BOUNDARY')

    def test_open_mesh_is_not_classified(self):
        self.assertEqual(classify_point([.5,.5,.5],VERTICES,FACES[:-1])['status'],'INVALID_MESH')

    def test_reversed_triangle_and_degenerate_rejected(self):
        reversed_faces=FACES.copy()
        reversed_faces[0]=reversed_faces[0][::-1]
        self.assertGreater(mesh_integrity(VERTICES,reversed_faces)['inconsistent_edge_winding'],0)
        duplicate=np.vstack([FACES,[0,0,1]])
        self.assertGreater(mesh_integrity(VERTICES,duplicate)['degenerate_triangles'],0)

    def test_concave_L_prism_rejects_bbox_false_positive(self):
        polygon=np.array([[0,0],[2,0],[2,1],[1,1],[1,2],[0,2]],float)
        vertices=np.vstack([np.column_stack([polygon,np.zeros(6)]),np.column_stack([polygon,np.ones(6)])])
        cap=[[0,1,3],[1,2,3],[0,3,5],[3,4,5]]
        faces=[triangle[::-1] for triangle in cap]+[[index+6 for index in triangle] for triangle in cap]
        for i in range(6):
            j=(i+1)%6
            faces.extend([[i,j,j+6],[i,j+6,i+6]])
        faces=np.array(faces)
        self.assertEqual(mesh_integrity(vertices,faces)['status'],'EDGE_CLOSED_ORIENTED')
        self.assertEqual(classify_point([1.5,1.5,.5],vertices,faces)['status'],'OUTSIDE_NUMERICAL')
        self.assertEqual(classify_point([.5,1.5,.5],vertices,faces)['status'],'INSIDE_NUMERICAL')

    def test_translation_does_not_change_parity(self):
        shifted=VERTICES+np.array([50,70,74])
        self.assertEqual(classify_point([50.5,70.5,74.5],shifted,FACES)['status'],'INSIDE_NUMERICAL')


if __name__=='__main__':
    unittest.main()
