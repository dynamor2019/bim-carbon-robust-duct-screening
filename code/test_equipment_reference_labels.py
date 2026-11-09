import unittest
import ifcopenshell
from audit_equipment_reference_labels import strings,matches


class DecodedLabelTests(unittest.TestCase):
    def test_aggregate_and_case_search(self):
        self.assertEqual(matches(('label',('302pf01',),'307Tk01')),['302PF01','307TK01'])
        self.assertEqual(matches((1.,None,False)),[])

    def test_entity_reference_not_recursively_searched(self):
        file=ifcopenshell.file(schema='IFC4')
        entity=file.create_entity('IfcPropertySingleValue',Name='302PF01')
        self.assertEqual(list(strings(entity)),[])
        typed=file.create_entity('IfcLabel','302PF01')
        self.assertEqual(matches(typed),['302PF01'])


if __name__=='__main__':
    unittest.main()
