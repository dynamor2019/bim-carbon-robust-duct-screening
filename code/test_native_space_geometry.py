import unittest
import numpy as np
import ifcopenshell
from native_space_geometry import curve_points,item_audit,profile_audit


class NativeSpaceTests(unittest.TestCase):
    def setUp(self):
        self.file=ifcopenshell.file(schema='IFC4')

    def test_positive_rectangle_extrusion_and_tangent_direction(self):
        profile=self.file.create_entity('IfcRectangleProfileDef',ProfileType='AREA',XDim=1000.,YDim=2000.)
        direction=self.file.create_entity('IfcDirection',DirectionRatios=(0.,0.,1.))
        solid=self.file.create_entity('IfcExtrudedAreaSolid',SweptArea=profile,ExtrudedDirection=direction,Depth=2500.)
        audit=item_audit(solid,np.eye(4),.001)
        self.assertEqual(audit['status'],'PASS_EXTRUSION_PROFILE_SCOPE')
        self.assertAlmostEqual(audit['profile_audit']['geometry_audit']['triangulated_area_m2'],2.)
        solid.ExtrudedDirection=self.file.create_entity('IfcDirection',DirectionRatios=(1.,0.,0.))
        self.assertEqual(item_audit(solid,np.eye(4),.001)['status'],'INVALID_EXTRUSION')

    def test_closed_polyline_and_self_crossing_profile(self):
        positions=[(0.,0.),(1.,1.),(0.,1.),(1.,0.),(0.,0.)]
        points=[self.file.create_entity('IfcCartesianPoint',Coordinates=p) for p in positions]
        curve=self.file.create_entity('IfcPolyline',Points=points)
        profile=self.file.create_entity('IfcArbitraryClosedProfileDef',ProfileType='AREA',OuterCurve=curve)
        self.assertEqual(profile_audit(profile,1.)['status'],'INVALID_PROFILE')
        curve.Points=points[:-1]
        self.assertEqual(curve_points(curve,1.)[1],'PROFILE_LOOP_NOT_EXPLICITLY_CLOSED')

    def test_void_profile_preserves_hole_area(self):
        def curve(coords):
            points=[self.file.create_entity('IfcCartesianPoint',Coordinates=p) for p in coords]
            return self.file.create_entity('IfcPolyline',Points=points)
        outer=curve([(0.,0.),(4.,0.),(4.,4.),(0.,4.),(0.,0.)])
        inner=curve([(1.,1.),(1.,2.),(2.,2.),(2.,1.),(1.,1.)])
        profile=self.file.create_entity('IfcArbitraryProfileDefWithVoids',ProfileType='AREA',OuterCurve=outer,InnerCurves=(inner,))
        report=profile_audit(profile,1.)
        self.assertEqual(report['status'],'SUPPORTED_PROFILE')
        self.assertAlmostEqual(report['geometry_audit']['net_area_m2'],15.)

    def test_indexed_line_chain_retains_explicit_closure(self):
        points=self.file.create_entity('IfcCartesianPointList2D',CoordList=((0.,0.),(1.,0.),(1.,1.),(0.,1.)))
        segment=self.file.create_entity('IfcLineIndex',(1,2,3,4,1))
        curve=self.file.create_entity('IfcIndexedPolyCurve',Points=points,Segments=(segment,))
        coords,status=curve_points(curve,1.)
        self.assertEqual(status,'SUPPORTED_CLOSED_STRAIGHT_PROFILE')
        self.assertEqual(coords.shape,(4,2))


if __name__=='__main__':
    unittest.main()
