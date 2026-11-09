"""Analytical software fixtures; no project physics parameters or engineering results."""
import math
import unittest
from candidate_pressure_loss import segment_loss,path_requirements


class PressureTests(unittest.TestCase):
    def test_analytical_and_distinct_reference_velocity(self):
        q=math.pi*.2**2/4*3
        row=segment_loss(q,10.,.2,1.,.02,[{'id':'k','coefficient':2.,'reference_velocity_m_s':4.,'reference':'FIXTURE_ONLY'}],'FIXTURE_DARCY')
        self.assertAlmostEqual(row['friction_loss_Pa'],4.5)
        self.assertAlmostEqual(row['local_losses'][0]['pressure_loss_Pa'],16.)
        self.assertAlmostEqual(row['total_pressure_loss_Pa'],20.5)

    def test_darcy_not_fanning_and_quadratic_scaling(self):
        a=segment_loss(.1,10.,.2,1.,.02,[],'FIXTURE')
        b=segment_loss(.2,10.,.2,1.,.02,[],'FIXTURE')
        self.assertAlmostEqual(b['friction_loss_Pa']/a['friction_loss_Pa'],4.)
        c=segment_loss(.1,20.,.2,1.,.02,[],'FIXTURE')
        self.assertAlmostEqual(c['friction_loss_Pa']/a['friction_loss_Pa'],2.)
        velocity=.1/(math.pi*.2**2/4)
        self.assertAlmostEqual(a['friction_loss_Pa'],.02*10/.2*velocity**2/2)

    def test_zero_and_missing_signed_coefficient_rejection(self):
        self.assertEqual(segment_loss(0.,1.,.2,1.,.02,[],'FIXTURE')['total_pressure_loss_Pa'],0.)
        for k in (-.1,float('nan'),True):
            with self.assertRaises(ValueError):
                segment_loss(.1,1.,.2,1.,.02,[{'id':'k','coefficient':k,'reference_velocity_m_s':2.,'reference':'FIXTURE'}],'FIXTURE')
        with self.assertRaises(ValueError):
            segment_loss(.1,1.,.2,1.,.02,[{'id':'k','coefficient':1.,'reference':'FIXTURE'}],'FIXTURE')
        with self.assertRaises(ValueError):
            segment_loss(.1,1.,.2,1.,None,[],'FIXTURE')

    def test_paths_keep_boundary_terms_and_no_double_sum(self):
        result=path_requirements({'t1':['a','c'],'t2':['b','c']},{'a':10.,'b':20.,'c':30.},{'t1':5.,'t2':6.},7.)
        self.assertEqual(result['maximum_path_requirement_Pa'],63.)
        self.assertEqual(result['additional_balancing_loss_Pa'],{'t1':11.,'t2':0.})
        self.assertFalse(result['fan_pressure_rise_certified'])

    def test_missing_boundary_extra_edge_and_repeated_path_rejected(self):
        for paths,losses,term in [({'t':['a']},{'a':1.},{}),({'t':['a']},{'a':1.,'extra':1.},{'t':0.}),({'t':['a','a']},{'a':1.},{'t':0.})]:
            with self.assertRaises(ValueError):
                path_requirements(paths,losses,term,0.)


if __name__=='__main__':
    unittest.main()
