"""Synthetic geometry fixtures only; no engineering experiment data."""
import unittest
import numpy as np
from recover_rectangular_interfaces import rectangle_fit,planar_groups,declared_circle_fit


class RectangularInterfaceTests(unittest.TestCase):
    def test_rotated_rectangle_with_collinear_vertices(self):
        xy=np.array([[0,0],[.5,0],[1,0],[1,.2],[0,.2]],dtype=float)
        u=np.array([1.,1.,0.])/np.sqrt(2)
        v=np.array([0.,0.,1.])
        points=np.array([3.,4.,5.])+xy[:,0,None]*u+xy[:,1,None]*v
        fit=rectangle_fit(points)
        self.assertIsNotNone(fit)
        np.testing.assert_allclose(sorted(fit['edge_lengths_m']),[.2,1.],atol=1e-10)

    def test_circle_trapezoid_and_warped_quad_rejected(self):
        angle=np.arange(12)*2*np.pi/12
        circle=np.column_stack((np.cos(angle),np.sin(angle),np.zeros(12)))
        trapezoid=np.array([[0,0,0],[1,0,0],[.8,1,0],[0,1,0]],float)
        warped=np.array([[0,0,0],[1,0,0],[1,1,.01],[0,1,0]],float)
        for points in (circle,trapezoid,warped):
            self.assertIsNone(rectangle_fit(points))

    def test_declared_hexagon_and_wrong_size_rejection(self):
        angle=np.arange(6)*2*np.pi/6
        points=np.column_stack((.1*np.cos(angle),.1*np.sin(angle),np.zeros(6)))
        self.assertIsNotNone(declared_circle_fit(points,.1))
        self.assertIsNone(declared_circle_fit(points,.125))

    def test_two_triangle_rectangle_patch_not_discarded(self):
        vertices=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0]],float)
        faces=np.array([[0,1,2],[0,2,3]])
        self.assertEqual(planar_groups(vertices,faces),[[0,1]])


if __name__=='__main__':
    unittest.main()
