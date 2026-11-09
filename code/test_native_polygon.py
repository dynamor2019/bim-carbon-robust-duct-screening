import unittest
from native_polygon_audit import polygon_boundary_incidence
from audit_architecture_declarations import declaration


class NativePolygonTests(unittest.TestCase):
    def test_closed_quad_cube_native_incidence(self):
        loops=[[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]
        report=polygon_boundary_incidence(loops)
        self.assertEqual(report['non_two_incident_edges'],0)
        self.assertEqual(report['inconsistent_edge_winding'],0)
        self.assertGreater(polygon_boundary_incidence(loops[:-1])['non_two_incident_edges'],0)

    def test_oriented_loop_mismatch_and_degenerate(self):
        report=polygon_boundary_incidence([[0,1,2],[0,1,2]])
        self.assertEqual(report['non_two_incident_edges'],0)
        self.assertEqual(report['inconsistent_edge_winding'],3)
        self.assertEqual(polygon_boundary_incidence([[0,0]])['degenerate_loops'],1)

    def test_decimal_comma_and_origin_not_location_heading(self):
        text='Origin location (x,y,z)\n Origin\n25505183.456 6706938.966 0,000\nLevel_05\n+72,310\nModels are not rotated in the project coordinate system'
        values=declaration(text)
        self.assertEqual(values['origin'],[25505183.456,6706938.966,0.])
        self.assertEqual(values['level05_m'],72.310)
        self.assertTrue(values['true_north_statement_present'])
        self.assertIsNone(declaration('not supplied')['origin'])


if __name__=='__main__':
    unittest.main()
