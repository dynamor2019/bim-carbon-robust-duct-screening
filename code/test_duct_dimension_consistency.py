import unittest
from audit_duct_dimension_consistency import check


def row(shape,label,d,w,h):
    return {'ifc_id':1,'guid':'SOFTWARE_ONLY','shape':shape,'properties':{'Koko (DU)':{'raw_value':label},
        **{k:{'raw_value':v,'value_mm':v,'nominal_value_type':'IfcPositiveLengthMeasure','property_id':i} for i,(k,v) in enumerate((('Halkaisija',d),('Leveys',w),('Korkeus',h)),2)}}}

class DimensionTests(unittest.TestCase):
    def test_circle_agrees_but_zero_type_violations_retained(self):
        r=check(row('CIRCULAR','Ø160',160.,0.,0.))
        self.assertTrue(r['status'].startswith('PASS'))
        self.assertEqual(len(r['positive_measure_domain_violations']),2)
        self.assertFalse(r['engineering_adopted'])
    def test_rectangle_orientation_not_sorted(self):
        self.assertTrue(check(row('RECTANGULAR','1400x800',0.,1400.,800.))['status'].startswith('PASS'))
        self.assertEqual(check(row('RECTANGULAR','800x1400',0.,1400.,800.))['status'],'UNRESOLVED_OR_MISMATCH')
    def test_unrecognized_or_different_label_fails(self):
        for label in ('Ø200','DN160','160',''):
            self.assertEqual(check(row('CIRCULAR',label,160.,0.,0.))['status'],'UNRESOLVED_OR_MISMATCH')

if __name__=='__main__': unittest.main()
