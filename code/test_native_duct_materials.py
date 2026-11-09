import unittest
import ifcopenshell
from audit_native_duct_materials import layers,plain

class NativeMaterialTests(unittest.TestCase):
    def test_layer_thickness_stays_native(self):
        model=ifcopenshell.file(schema='IFC4')
        material=model.create_entity('IfcMaterial',Name='SOFTWARE_ONLY')
        layer=model.create_entity('IfcMaterialLayer',Material=material,LayerThickness=.5)
        layer_set=model.create_entity('IfcMaterialLayerSet',MaterialLayers=[layer])
        result=layers(layer_set)
        self.assertEqual(result[0]['layer_thickness_native'],.5)
        self.assertEqual(result[0]['material']['name'],'SOFTWARE_ONLY')

    def test_layer_usage_preserves_layer_set_evidence(self):
        model=ifcopenshell.file(schema='IFC4')
        material=model.create_entity('IfcMaterial',Name='SOFTWARE_ONLY')
        layer=model.create_entity('IfcMaterialLayer',Material=material,LayerThickness=.7)
        layer_set=model.create_entity('IfcMaterialLayerSet',MaterialLayers=[layer])
        usage=model.create_entity('IfcMaterialLayerSetUsage',ForLayerSet=layer_set,LayerSetDirection='AXIS2',DirectionSense='POSITIVE',OffsetFromReferenceLine=0.)
        self.assertEqual(layers(usage)[0]['layer_thickness_native'],.7)

    def test_no_material_is_missing_not_zero_thickness(self):
        self.assertEqual(layers(None),[])
        self.assertIsNone(plain(None))

if __name__=='__main__': unittest.main()
