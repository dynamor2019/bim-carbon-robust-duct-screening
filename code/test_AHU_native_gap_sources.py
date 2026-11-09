import unittest
import numpy as np
from audit_AHU_native_gap_sources import rim_samples


class SourceRimProbeTests(unittest.TestCase):
    def test_plane_radius_translation_and_general_normal(self):
        center=np.array([48.,59.,73.9])
        normal=np.array([1.,2.,3.])
        points=rim_samples(center,normal,.2)
        self.assertEqual(points.shape,(16,3))
        np.testing.assert_allclose(np.linalg.norm(points-center,axis=1),.2,atol=1e-12)
        np.testing.assert_allclose((points-center)@normal,0.,atol=1e-12)
        np.testing.assert_allclose(points.mean(axis=0),center,atol=1e-12)


if __name__=='__main__':
    unittest.main()
