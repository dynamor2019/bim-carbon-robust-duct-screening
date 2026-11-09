import itertools,unittest
from audit_alignment_registration import compare


class LocalMarkerTests(unittest.TestCase):
    def test_equal_asymmetric_marker_and_shifted_marker(self):
        corners=[list(c) for c in itertools.product((0.,1.),(0.,2.),(0.,3.))]
        marker={'geometry':{'min_m':[0.,0.,0.],'max_m':[1.,2.,3.],'unique_vertices_m':corners}}
        self.assertEqual(compare(marker,marker)['status'],'PASS_LOCAL_MARKER_COORDINATES_ONLY')
        shifted={'geometry':{'min_m':[.01,0.,0.],'max_m':[1.01,2.,3.],'unique_vertices_m':corners}}
        self.assertEqual(compare(marker,shifted)['status'],'FAIL_LOCAL_MARKER_COORDINATES')
        rotated={'geometry':{'min_m':[0.,0.,0.],'max_m':[2.,1.,3.],'unique_vertices_m':corners}}
        self.assertEqual(compare(marker,rotated)['status'],'FAIL_LOCAL_MARKER_COORDINATES')


if __name__=='__main__':
    unittest.main()
