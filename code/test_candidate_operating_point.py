"""Curve geometry arithmetic fixtures only, not a project fan/system model."""
import unittest
from candidate_operating_point import intersections


def curve(rows):
    return {'pressure_basis':'fan_total','conditions':{'test':'SOFTWARE_ONLY'},'source_ref':'SOFTWARE_ONLY',
        'points':[{'flow_m3_s':q,'pressure_Pa':p} for q,p in rows]}


def run(f,s):
    return intersections(curve(f),curve(s),'fan_total',1e-9,1e-10)


class OperatingPointTests(unittest.TestCase):
    def test_analytical_unique_root_and_net_slope(self):
        result=run([(0.,100.),(2.,0.)],[(0.,0.),(2.,100.)])
        self.assertEqual(result['status'],'UNIQUE_NUMERICAL_INTERSECTION')
        self.assertAlmostEqual(result['points'][0]['flow_m3_s'],1.)
        self.assertAlmostEqual(result['points'][0]['fan_pressure_Pa'],50.)
        self.assertTrue(result['points'][0]['negative_net_slope_on_all_adjacent_segments'])
        self.assertFalse(result['actual_operation_certified'])

    def test_multiple_roots_retained(self):
        result=run([(0.,10.),(1.,0.),(2.,10.),(3.,0.)],[(0.,5.),(3.,5.)])
        self.assertEqual(result['status'],'MULTIPLE_INTERSECTIONS')
        self.assertEqual([r['flow_m3_s'] for r in result['points']],[.5,1.5,2.5])
        self.assertFalse(result['points'][1]['negative_net_slope_on_all_adjacent_segments'])

    def test_coincident_interval_not_unique_point(self):
        result=run([(0.,10.),(2.,10.)],[(0.,10.),(2.,10.)])
        self.assertEqual(result['status'],'AMBIGUOUS_COINCIDENT_INTERVAL')
        self.assertEqual(len(result['coincident_intervals']),1)

    def test_knot_root_has_both_sides_and_is_deduplicated(self):
        result=run([(0.,10.),(1.,5.),(2.,0.)],[(0.,0.),(1.,5.),(2.,10.)])
        self.assertEqual(len(result['points']),1)
        self.assertEqual(len(result['points'][0]['adjacent_net_slopes_Pa_per_m3_s']),2)

    def test_no_intersection_and_no_extrapolation(self):
        self.assertEqual(run([(0.,10.),(1.,9.)],[(0.,1.),(1.,2.)])['status'],'NO_INTERSECTION')
        self.assertEqual(run([(0.,10.),(1.,9.)],[(2.,1.),(3.,2.)])['status'],'NO_COMMON_INTERVAL')

    def test_mismatched_pressure_and_invalid_tolerance(self):
        f=curve([(0.,10.),(1.,0.)])
        s=curve([(0.,0.),(1.,10.)])
        with self.assertRaises(ValueError):
            intersections(f,dict(s,pressure_basis='fan_static'),'fan_total',1e-9,1e-10)
        with self.assertRaises(ValueError):
            intersections(f,s,'fan_total',0.,1e-10)


if __name__=='__main__':
    unittest.main()
