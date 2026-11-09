"""Independent matcher fixtures, not physical connectivity evidence."""
import unittest
from audit_network_interfaces import independent_pairs


def port(label,element,x,radius=.1,normal=(0.,0.,1.)):
    return {'port_id':label,'ifc_id':element,'center_m':[x,0.,0.],
            'normal_sign_arbitrary':list(normal),'radii_m':[radius]}


class IndependentInterfaceTests(unittest.TestCase):
    def test_sorted_window_negative_coordinates(self):
        ports=[port('c',3,.2),port('b',2,-.000002),port('a',1,-.000003)]
        criteria={'center_m':1e-5,'radius_m':1e-5,'angle_deg':.01}
        self.assertEqual(independent_pairs(ports,criteria),{('a','b')})

    def test_recompute_preserves_all_ambiguous_pairs(self):
        ports=[port('a',1,0.),port('b',2,0.),port('c',3,0.)]
        criteria={'center_m':1e-5,'radius_m':1e-5,'angle_deg':.01}
        self.assertEqual(independent_pairs(ports,criteria),{('a','b'),('a','c'),('b','c')})

    def test_different_radius_or_axis_rejected(self):
        ports=[port('a',1,0.),port('b',2,0.,radius=.2),port('c',3,0.,normal=(1.,0.,0.))]
        criteria={'center_m':1e-5,'radius_m':1e-5,'angle_deg':.01}
        self.assertEqual(independent_pairs(ports,criteria),set())


if __name__=='__main__':
    unittest.main()
