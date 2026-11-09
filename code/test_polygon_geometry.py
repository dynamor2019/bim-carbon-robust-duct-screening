import unittest
import json
import numpy as np
from polygon_geometry import face_analysis


class PolygonGeometryTests(unittest.TestCase):
    def test_concave_area_and_reversed_winding(self):
        points=np.array([[0,0,0],[2,0,0],[2,1,0],[1,1,0],[1,2,0],[0,2,0]],float)
        for polygon in (points,points[::-1],points+[50,70,74]):
            result=face_analysis(polygon)
            self.assertEqual(result['status'],'PLANAR_SIMPLE_TRIANGULATED')
            self.assertEqual(len(result['triangles']),4)
            self.assertAlmostEqual(result['triangulated_area_m2'],3.)

    def test_nonplanar_and_self_crossing_rejected(self):
        nonplanar=[[0,0,0],[1,0,0],[1,1,.01],[0,1,0]]
        self.assertEqual(face_analysis(nonplanar)['status'],'INVALID_FOR_PLANAR_TRIANGULATION')
        crossing=[[0,0,0],[1,1,0],[0,1,0],[1,0,0]]
        report=face_analysis(crossing)
        self.assertTrue(report['nonadjacent_intersections'])
        self.assertEqual(report['intersection_details'][0]['kind'],'PROPER_CROSSING')

    def test_result_json_serialization(self):
        for points in ([[0,0,0],[1,0,0],[0,1,0]],[[0,0,0],[1,0,0],[1,0,0],[0,1,0]]):
            result=face_analysis(points)
            self.assertEqual(json.loads(json.dumps(result)),result)

    def test_duplicate_edge_and_small_face(self):
        self.assertGreater(face_analysis([[0,0,0],[1,0,0],[1,0,0],[0,1,0]])['zero_length_edges'],0)
        result=face_analysis([[0,0,0],[.01,0,0],[0,.01,0]])
        self.assertEqual(result['status'],'PLANAR_SIMPLE_TRIANGULATED')
        self.assertAlmostEqual(result['triangulated_area_m2'],.00005)


if __name__=='__main__':
    unittest.main()
