import unittest
from audit_fan_schedule_identity import section


class ScheduleSectionTests(unittest.TestCase):
    def test_designation_boundary_and_blanks_retained(self):
        text='G3 302 PF 01 Poistoilmapuhallin\nPoistoilmavirta m³/s 3,6\nKokonaishyötysuhde %\nG3 302 FZ 22 Moottoripelti'
        value=section(text,r'G3\s+302\s+PF\s+01')
        self.assertIn('Kokonaishyötysuhde %',value)
        self.assertNotIn('FZ 22',value)
        with self.assertRaises(ValueError):
            section(text,'missing')


if __name__=='__main__':
    unittest.main()
