"""Tests for numerical feature matching; fixture values are not engineering data."""
import unittest
from extract_network_interfaces import group_features,match_features


def port(identifier,element,center,normal=(0.,0.,1.),radii=(.1,)):
    return {'port_id':identifier,'ifc_id':element,'center_m':list(center),
            'normal_sign_arbitrary':list(normal),'radii_m':list(radii)}


class NetworkInterfaceTests(unittest.TestCase):
    def test_neighbor_grid_cells_and_normal_sign(self):
        features=[port('a',1,(.999999e-5,0.,0.)),port('b',2,(1.000001e-5,0.,0.),(0.,0.,-1.))]
        pairs=match_features(features)
        self.assertEqual(len(pairs),1)
        self.assertEqual(pairs[0]['axis_normal_angle_deg'],0.)

    def test_radius_normal_and_same_entity_rejection(self):
        a=port('a',1,(0.,0.,0.))
        for other in [port('b',2,(0.,0.,0.),radii=(.11,)),
                      port('b',2,(0.,0.,0.),normal=(1.,0.,0.)),
                      port('b',1,(0.,0.,0.))]:
            self.assertEqual(match_features([a,other]),[])

    def test_ambiguity_preserved(self):
        features=[port('a',1,(0.,0.,0.)),port('b',2,(0.,0.,0.)),port('c',3,(0.,0.,0.))]
        self.assertEqual(len(match_features(features)),3)

    def test_concentric_inner_outer_rims_grouped(self):
        features=[{'center_m':[0.,0.,0.],'normal_sign_arbitrary':[0.,0.,1.],'radius_m':.1,'origin':'outer'},
                  {'center_m':[0.,0.,0.],'normal_sign_arbitrary':[0.,0.,-1.],'radius_m':.098,'origin':'inner'}]
        groups=group_features(features)
        self.assertEqual(len(groups),1)
        self.assertEqual(groups[0]['radii_m'],[.098,.1])
        self.assertEqual(len(groups[0]['origins']),2)


if __name__=='__main__':
    unittest.main()
