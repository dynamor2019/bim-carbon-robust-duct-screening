"""Arithmetic curve fixtures only; not manufacturer or project fan selections."""
import copy
import unittest
from candidate_fan_curve import screen_curve


def fixture():
    return {'pressure_basis':'fan_total','power_basis':'electrical_input','source_ref':'SOFTWARE_ONLY',
        'conditions':{'density_kg_m3':1.,'speed_rpm':1000.,'installation_category':'FIXTURE'},
        'stable_flow_interval_m3_s':[1.,3.],
        'points':[{'flow_m3_s':1.,'pressure_Pa':300.,'electrical_power_W':1000.},{'flow_m3_s':3.,'pressure_Pa':100.,'electrical_power_W':1200.}]}


class FanCurveTests(unittest.TestCase):
    def test_interpolation_and_capacity_not_equilibrium(self):
        c=fixture()
        row=screen_curve(c,2.,150.,'fan_total',c['conditions'])
        self.assertEqual(row['curve_pressure_Pa'],200.)
        self.assertEqual(row['electrical_power_W'],1100.)
        self.assertEqual(row['pressure_margin_Pa'],50.)
        self.assertFalse(row['equilibrium_certified'])
        self.assertEqual(screen_curve(c,2.,210.,'fan_total',c['conditions'])['status'],'FAIL_INSUFFICIENT_PRESSURE')

    def test_endpoints_supported_but_no_extrapolation(self):
        c=fixture()
        self.assertEqual(screen_curve(c,1.,300.,'fan_total',c['conditions'])['curve_pressure_Pa'],300.)
        self.assertEqual(screen_curve(c,3.,100.,'fan_total',c['conditions'])['electrical_power_W'],1200.)
        row=screen_curve(c,4.,50.,'fan_total',c['conditions'])
        self.assertEqual(row['status'],'FAIL_OUTSIDE_CURVE_SUPPORT')
        self.assertIsNone(row['electrical_power_W'])

    def test_pressure_shaft_power_and_condition_mismatch_rejected(self):
        c=fixture()
        with self.assertRaises(ValueError):
            screen_curve(c,2.,150.,'fan_static',c['conditions'])
        with self.assertRaises(ValueError):
            screen_curve(dict(c,power_basis='shaft'),2.,150.,'fan_total',c['conditions'])
        with self.assertRaises(ValueError):
            screen_curve(c,2.,150.,'fan_total',dict(c['conditions'],density_kg_m3=1.2))

    def test_stall_interval_and_unsorted_duplicate_points(self):
        c=fixture()
        c['stable_flow_interval_m3_s']=[2.,3.]
        self.assertEqual(screen_curve(c,1.5,100.,'fan_total',c['conditions'])['status'],'FAIL_OUTSIDE_STABLE_INTERVAL')
        for points in (list(reversed(c['points'])),[c['points'][0],c['points'][0]]):
            with self.assertRaises(ValueError):
                screen_curve(dict(c,points=points),2.,100.,'fan_total',c['conditions'])

    def test_missing_power_and_curve_source_rejected(self):
        c=fixture()
        for value in (None,float('nan'),True):
            bad=copy.deepcopy(c)
            bad['points'][0]['electrical_power_W']=value
            with self.assertRaises(ValueError):
                screen_curve(bad,2.,150.,'fan_total',c['conditions'])
        with self.assertRaises(ValueError):
            screen_curve(dict(c,source_ref=''),2.,150.,'fan_total',c['conditions'])


if __name__=='__main__':
    unittest.main()
