import tempfile,unittest
from pathlib import Path
from audit_whole_ifc_connectivity import scan

class WholeIFCScanTests(unittest.TestCase):
    def test_multiline_and_zero_kind_retention(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'fixture.ifc'
            path.write_text("ISO-10303-21;\nDATA;\n#1=IFCDISTRIBUTIONPORT('FIXTURE',$,$,$,$,$,$,$,$,$);\n#2=IFCRELCONNECTSPORTS(\n'FIXTURE',$,$,$,#1,#3,$);\n#3=IFCDISTRIBUTIONPORT('FIXTURE2',$,$,$,$,$,$,$,$,$);\nENDSEC;\n",encoding='utf-8')
            result=scan(path)
            self.assertEqual(result['entity_count'],3)
            self.assertEqual(result['selected_kind_counts']['IFCRELCONNECTSPORTS'],1)
            self.assertEqual(result['selected_kind_counts']['IFCRELCONNECTSELEMENTS'],0)
            self.assertEqual(result['records'][1]['reference_ids'],[1,3])
    def test_unterminated_entity_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'fixture.ifc'; path.write_text('#1=IFCDISTRIBUTIONPORT(',encoding='utf-8')
            with self.assertRaises(ValueError): scan(path)

if __name__=='__main__': unittest.main()
