import unittest
from audit_duct_material_table import pair_rows


def lines():
    result=[]
    for i in range(7):
        y=100+i*80
        result.extend([{'text':'Pyöreä kierresauma, FIXTURE '+str(i),'bbox':[90,y,270,y+9]},
            {'text':'Seinämäpaksuus mm','bbox':[90,y+30,170,y+39]},
            {'text':'0,5','bbox':[360,y+30,375,y+39]}])
    return result


class MaterialPairTests(unittest.TestCase):
    def test_reversed_extraction_order(self):
        self.assertEqual([r['wall_thickness_mm'] for r in pair_rows(list(reversed(lines())))],[.5]*7)

    def test_duplicate_value_rejected(self):
        rows=lines()
        rows.append(dict(rows[2]))
        with self.assertRaises(ValueError): pair_rows(rows)

    def test_shifted_or_missing_value_rejected(self):
        rows=lines()
        rows[2]['bbox']=[360,131,375,140]
        with self.assertRaises(ValueError): pair_rows(rows)
        with self.assertRaises(ValueError): pair_rows(lines()[:-1])

if __name__=='__main__': unittest.main()
