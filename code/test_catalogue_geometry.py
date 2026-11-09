"""Reference catalogue units and ambiguous-polygon geometry regression tests."""
import unittest
import numpy as np
from qualify_lindab_catalogue import parse_weights
from inspect_prl_interfaces import cyclic_polygon


class CatalogueGeometryTests(unittest.TestCase):
    def test_mass_per_metre_not_per_stock_piece(self):
        text='Standard weight (kg/m)\n160 3000 1.64\n315 3000 4.02\n'
        words=[]
        for y,tokens in [(10,['160','3000','1.64']),(20,['315','3000','4.02'])]:
            words.extend((x,y,x+5,y+2,token,0,0,0) for x,token in zip([0,100,200],tokens))
        rows=parse_weights(text,words)
        self.assertEqual(rows[0]['mass_kg_per_m'],1.64)
        self.assertEqual(rows[0]['stock_length_mm'],3000)
        self.assertEqual(rows[1]['mass_kg_per_m'],4.02)

    def test_coordinate_disagreement_rejected(self):
        text='Standard weight (kg/m)\n160 3000 1.64\n'
        words=[(0,10,5,12,'160',0,0,0),(100,10,105,12,'3000',0,0,0),(200,10,205,12,'9.99',0,0,0)]
        with self.assertRaises(ValueError):
            parse_weights(text,words)

    def test_cyclic_square_remains_explicitly_ambiguous(self):
        square=np.array([[1.,0.,0.],[0.,1.,0.],[-1.,0.,0.],[0.,-1.,0.]])
        result=cyclic_polygon(square)
        self.assertAlmostEqual(result['radius_m'],1.)
        self.assertIn('actual square',result['geometry_limit'])
        self.assertIsNone(cyclic_polygon(np.array([[0.,0.,0.],[2.,0.,0.],[2.,1.,0.],[0.,1.,0.]])))


if __name__=='__main__':
    unittest.main()
