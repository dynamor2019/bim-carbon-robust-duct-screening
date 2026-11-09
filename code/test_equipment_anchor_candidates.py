import unittest
from audit_equipment_anchor_candidates import relevant


class EquipmentScopeTests(unittest.TestCase):
    def test_multigroup_scope_does_not_drop_other_assignments(self):
        groups=[{'group_name':'307TK01 (saunaosasto)'},{'group_name':'302PK01 (toimistot, oikea)'}]
        self.assertTrue(relevant(groups))
        self.assertEqual(len(groups),2)
        self.assertFalse(relevant([{'group_name':'301PK01'},{'group_name':None}]))


if __name__=='__main__':
    unittest.main()
