"""Ledger arithmetic fixtures, not installed EPD factors or measured energy."""
import copy
import unittest
from candidate_carbon_ledger import ledger


def factor(value,module='A1-A3',unit='kgCO2e/kg'):
    return {'state':'DECLARED','value':value,'indicator':'GWP-total','unit':unit,'module':module,'source_ref':'SOFTWARE_ONLY'}


def fixture():
    materials=[{'id':'duct','mass_kg':10.,'mass_ref':'SOFTWARE_ONLY','initial_factor':factor(2.),'replacement_events':[
        {'year':5.,'mass_kg':10.,'factor':factor(3.),'source_ref':'SOFTWARE_ONLY'}]}]
    periods=[{'id':'p','start_year':0.,'end_year':10.,'electricity_kWh':100.,'energy_ref':'SOFTWARE_ONLY','grid_factor':factor(.5,'B6','kgCO2e/kWh')}]
    boundary={'modules':['A1-A3','B4','B6'],'replacement_scope':'PRODUCTION_ONLY','excluded_burdens':['replacement transport installation disposal','other stages'],'source_ref':'SOFTWARE_ONLY'}
    return materials,periods,boundary


class CarbonLedgerTests(unittest.TestCase):
    def test_exact_stage_sum(self):
        m,p,b=fixture()
        row=ledger(m,p,10.,'GWP-total',b)
        self.assertEqual(row['totals'],{'A1-A3_kgCO2e':20.,'B4_replacement_production_kgCO2e':30.,'B6_kgCO2e':50.,'selected_stage_sum_kgCO2e':100.})
        self.assertFalse(row['whole_life_LCA'])
        self.assertFalse(row['installed_product_applicability_certified'])

    def test_MND_MNR_wrong_indicator_and_unit_rejected(self):
        for field,value in [('state','MND'),('state','MNR'),('value',None),('indicator','GWP-fossil'),('unit','kgCO2e/unit')]:
            m,p,b=fixture()
            m[0]['initial_factor'][field]=value
            with self.assertRaises(ValueError):
                ledger(m,p,10.,'GWP-total',b)

    def test_negative_declared_factor_not_clipped(self):
        m,p,b=fixture()
        m[0]['initial_factor']=factor(-2.)
        self.assertEqual(ledger(m,p,10.,'GWP-total',b)['totals']['A1-A3_kgCO2e'],-20.)

    def test_no_replacement_defaults_and_horizon_end_excluded(self):
        m,p,b=fixture()
        m[0]['replacement_events']=[]
        self.assertEqual(ledger(m,p,10.,'GWP-total',b)['totals']['B4_replacement_production_kgCO2e'],0.)
        for events in (None,[{'year':10.,'mass_kg':1.,'factor':factor(2.),'source_ref':'SOFTWARE_ONLY'}]):
            m[0]['replacement_events']=events
            with self.assertRaises(ValueError):
                ledger(m,p,10.,'GWP-total',b)

    def test_energy_period_gaps_overlap_and_duplicate_material(self):
        m,p,b=fixture()
        for start,end in ((1.,10.),(0.,9.)):
            bad=copy.deepcopy(p)
            bad[0].update(start_year=start,end_year=end)
            with self.assertRaises(ValueError):
                ledger(m,bad,10.,'GWP-total',b)
        with self.assertRaises(ValueError):
            ledger(m+m,p,10.,'GWP-total',b)
        with self.assertRaises(ValueError):
            ledger(m,p+p,10.,'GWP-total',b)

    def test_explicit_zero_energy_and_missing_energy(self):
        m,p,b=fixture()
        p[0]['electricity_kWh']=0.
        self.assertEqual(ledger(m,p,10.,'GWP-total',b)['totals']['B6_kgCO2e'],0.)
        for value in (None,float('nan'),True,-1.):
            p[0]['electricity_kWh']=value
            with self.assertRaises(ValueError):
                ledger(m,p,10.,'GWP-total',b)


if __name__=='__main__':
    unittest.main()
