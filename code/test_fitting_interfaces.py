"""Synthetic unit fixtures only; these are not engineering case results."""
import unittest
import numpy as np
from recover_fitting_interfaces import circle_fit,recover_rims


def tube_mesh(closed):
    n=16
    angles=np.arange(n)*2*np.pi/n
    vertices=[]
    for z,radius in [(0.,1.),(2.,1.),(0.,.8),(2.,.8)]:
        vertices.extend(np.column_stack((radius*np.cos(angles),radius*np.sin(angles),np.full(n,z))))
    faces=[]
    def strip(first,second):
        for i in range(n):
            j=(i+1)%n
            faces.extend([[first+i,first+j,second+i],[first+j,second+j,second+i]])
    strip(0,n)
    if closed:
        strip(2*n,3*n)
        strip(0,2*n)
        strip(n,3*n)
    return np.array(vertices),np.array(faces,dtype=int)


class InterfaceTests(unittest.TestCase):
    def test_planar_circle_and_rejections(self):
        angles=np.arange(16)*2*np.pi/16
        points=np.column_stack((3+2*np.cos(angles),-1+2*np.sin(angles),np.full(16,7.)))
        result=circle_fit(points)
        np.testing.assert_allclose(result['center_m'],[3.,-1.,7.],atol=1e-10)
        self.assertAlmostEqual(result['radius_m'],2.)
        ellipse=points.copy()
        ellipse[:,0]=3+3*np.cos(angles)
        self.assertIsNone(circle_fit(ellipse))
        warped=points.copy()
        warped[0,2]+=.01
        self.assertIsNone(circle_fit(warped))

    def test_open_tube_two_boundary_rims(self):
        vertices,faces=tube_mesh(False)
        recovered=recover_rims(vertices,faces)
        self.assertEqual(recovered['whole_mesh_loop_count'],2)
        self.assertEqual(len(recovered['rims']),2)
        self.assertEqual(recovered['nonmanifold_edge_count'],0)

    def test_closed_annular_tube_has_four_patch_rims(self):
        vertices,faces=tube_mesh(True)
        recovered=recover_rims(vertices,faces)
        self.assertEqual(recovered['whole_mesh_loop_count'],0)
        self.assertEqual(len(recovered['rims']),4)
        self.assertEqual(recovered['nonmanifold_edge_count'],0)
        self.assertEqual(sorted(round(r['radius_m'],6) for r in recovered['rims']),[.8,.8,1.,1.])


if __name__=='__main__':
    unittest.main()
