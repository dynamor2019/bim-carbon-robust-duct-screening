"""IFC prefix powers and typed unit inheritance regressions."""
import unittest
from resolve_ifc_units import scale_to_si,resolve_property


def si(name,prefix,unit_type):
    return {'type':'IfcSIUnit','Name':name,'Prefix':prefix,'UnitType':unit_type}


class IFCUnitTests(unittest.TestCase):
    def test_deci_cubic_metres_are_litres(self):
        volume=si('CUBIC_METRE','DECI','VOLUMEUNIT')
        self.assertAlmostEqual(scale_to_si(volume),.001)
        self.assertAlmostEqual(scale_to_si(si('SQUARE_METRE','MILLI','AREAUNIT')),1e-6)
        self.assertAlmostEqual(scale_to_si(si('GRAM','KILO','MASSUNIT')),1.)

    def test_typed_inheritance_and_velocity_uses_own_metre_unit(self):
        volume=si('CUBIC_METRE','DECI','VOLUMEUNIT')
        second=si('SECOND',None,'TIMEUNIT')
        flow={'type':'IfcDerivedUnit','UnitType':'VOLUMETRICFLOWRATEUNIT','Elements':[{'Unit':volume,'Exponent':1},{'Unit':second,'Exponent':-1}]}
        velocity={'type':'IfcDerivedUnit','UnitType':'LINEARVELOCITYUNIT','Elements':[{'Unit':si('METRE',None,'LENGTHUNIT'),'Exponent':1},{'Unit':second,'Exponent':-1}]}
        assigned=[flow,velocity,si('METRE','MILLI','LENGTHUNIT')]
        self.assertAlmostEqual(resolve_property({'nominal_value_type':'IfcVolumetricFlowRateMeasure','explicit_unit':None},assigned)['scale_to_SI'],.001)
        self.assertEqual(resolve_property({'nominal_value_type':'IfcLinearVelocityMeasure','explicit_unit':None},assigned)['scale_to_SI'],1.)
        self.assertIsNone(resolve_property({'nominal_value_type':'IfcReal','explicit_unit':None},assigned))

    def test_missing_or_ambiguous_context_rejected(self):
        prop={'nominal_value_type':'IfcLinearVelocityMeasure','explicit_unit':None}
        with self.assertRaises(ValueError):
            resolve_property(prop,[])


if __name__=='__main__':
    unittest.main()
