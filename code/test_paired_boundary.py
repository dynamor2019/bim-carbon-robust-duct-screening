"""Test mesh-distance evidence and deterministic candidate-path tracing."""
import unittest
import ifcopenshell
import numpy as np
from types import SimpleNamespace
from unittest.mock import patch
from verify_paired_boundary import nearest_vertex_distance, extrusion_axes, indexed_circle_center
from trace_candidate_path import shortest_path


class PairedBoundaryTests(unittest.TestCase):
    def test_vertex_distance_symmetric_and_shared_vertices(self):
        a=np.array([[0.,0.,0.],[1.,0.,0.]])
        b=np.array([[1.,0.,0.],[2.,0.,0.]])
        self.assertEqual(nearest_vertex_distance(a,b),0.)
        self.assertEqual(nearest_vertex_distance(a,b),nearest_vertex_distance(b,a))

    def test_vertex_search_across_chunk_boundaries(self):
        a=np.zeros((260,3))
        a[-1]=[10.,0.,0.]
        b=np.array([[10.1,0.,0.]])
        self.assertAlmostEqual(nearest_vertex_distance(a,b),.1)

    def test_original_extrusion_axis_with_mapping_and_units(self):
        profile=SimpleNamespace(Position=None, Radius=50.,
            is_a=lambda kind=None: kind=='IfcCircleProfileDef' if kind else 'IfcCircleProfileDef')
        solid=SimpleNamespace(Position=None,SweptArea=profile,Depth=100.,
            ExtrudedDirection=SimpleNamespace(DirectionRatios=(0.,0.,2.)),
            is_a=lambda kind:kind=='IfcExtrudedAreaSolid', id=lambda:7)
        mapped=SimpleNamespace(is_a=lambda kind:kind=='IfcMappedItem',
            MappingSource=SimpleNamespace(MappedRepresentation=SimpleNamespace(Items=[solid])))
        entity=SimpleNamespace(ObjectPlacement=object(),Representation=SimpleNamespace(
            Representations=[SimpleNamespace(RepresentationIdentifier='Body',Items=[mapped])]))
        placement=np.eye(4)
        placement[1,3]=200.
        mapping=np.array([[0.,0.,1.,100.],[0.,1.,0.,0.],[-1.,0.,0.,0.],[0.,0.,0.,1.]])
        with patch('verify_paired_boundary.ifcopenshell.util.placement.get_local_placement',return_value=placement), \
             patch('verify_paired_boundary.ifcopenshell.util.placement.get_mappeditem_transformation',return_value=mapping):
            axes=extrusion_axes(entity,.001)
        np.testing.assert_allclose(axes[0]['end_a_m'],[.1,.2,0.])
        np.testing.assert_allclose(axes[0]['end_b_m'],[.2,.2,0.])
        self.assertAlmostEqual(axes[0]['axis_length_m'],.1)

    def test_polygon_profile_center_and_orientation(self):
        coords=[(1.,2.),(3.,2.),(3.,4.),(1.,4.),(1.,2.)]
        for points in (coords, coords[::-1]):
            outer=SimpleNamespace(is_a=lambda kind:kind=='IfcPolyline',
                Points=[SimpleNamespace(Coordinates=p) for p in points])
            profile=SimpleNamespace(OuterCurve=outer,
                is_a=lambda kind=None:False if kind else 'IfcArbitraryClosedProfileDef')
            solid=SimpleNamespace(Position=None,SweptArea=profile,Depth=100.,
                ExtrudedDirection=SimpleNamespace(DirectionRatios=(0.,0.,1.)),
                is_a=lambda kind:kind=='IfcExtrudedAreaSolid',id=lambda:8)
            entity=SimpleNamespace(ObjectPlacement=object(),Representation=SimpleNamespace(
                Representations=[SimpleNamespace(RepresentationIdentifier='Body',Items=[solid])]))
            with patch('verify_paired_boundary.ifcopenshell.util.placement.get_local_placement',return_value=np.eye(4)):
                axes=extrusion_axes(entity,.001)
            np.testing.assert_allclose(axes[0]['end_a_m'],[.002,.003,0.])
            np.testing.assert_allclose(axes[0]['end_b_m'],[.002,.003,.1])

    def test_indexed_circle_center_and_non_circular_rejection(self):
        angles=np.linspace(0,2*np.pi,13)
        points=np.column_stack((7+3*np.cos(angles),-4+3*np.sin(angles)))
        model=ifcopenshell.file(schema='IFC4')
        arcs=[model.create_entity('IfcArcIndex',values) for values in [(1,3,5),(5,7,9),(9,11,1)]]
        curve=SimpleNamespace(Points=SimpleNamespace(CoordList=points.tolist()),Segments=arcs)
        np.testing.assert_allclose(indexed_circle_center(curve),[7.,-4.],atol=1e-10)
        bad=points.copy()
        bad[5,0]+=.1
        self.assertIsNone(indexed_circle_center(SimpleNamespace(Points=SimpleNamespace(CoordList=bad.tolist()),Segments=arcs)))
        self.assertIsNone(indexed_circle_center(SimpleNamespace(Points=SimpleNamespace(CoordList=[[0.,0.],[1.,0.],[2.,0.]]))))

    def test_indexed_rectangle_is_not_circle_and_retains_axis(self):
        coords=[(-700.,-400.),(700.,-400.),(700.,400.),(-700.,400.),(-700.,-400.)]
        model=ifcopenshell.file(schema='IFC4')
        for segments in (None,[model.create_entity('IfcLineIndex',(1,2,3,4,1))]):
            outer=SimpleNamespace(Points=SimpleNamespace(CoordList=coords),Segments=segments,
                is_a=lambda kind:kind=='IfcIndexedPolyCurve')
            self.assertIsNone(indexed_circle_center(outer))
            profile=SimpleNamespace(OuterCurve=outer,is_a=lambda kind=None:False if kind else 'IfcArbitraryProfileDefWithVoids')
            solid=SimpleNamespace(Position=None,SweptArea=profile,Depth=80.,
                ExtrudedDirection=SimpleNamespace(DirectionRatios=(0.,0.,1.)),
                is_a=lambda kind:kind=='IfcExtrudedAreaSolid',id=lambda:9)
            entity=SimpleNamespace(ObjectPlacement=object(),Representation=SimpleNamespace(
                Representations=[SimpleNamespace(RepresentationIdentifier='Body',Items=[solid])]))
            with patch('verify_paired_boundary.ifcopenshell.util.placement.get_local_placement',return_value=np.eye(4)):
                axes=extrusion_axes(entity,.001)
            self.assertIsNone(axes[0]['source_outer_radius_m'])
            np.testing.assert_allclose(axes[0]['end_a_m'],[0.,0.,0.])
            self.assertAlmostEqual(axes[0]['axis_length_m'],.08)

    def test_path_does_not_cross_missing_bridge(self):
        adjacency={'a':{'bridge'},'bridge':{'a','b'},'b':{'bridge'},'island':set()}
        self.assertEqual(shortest_path(adjacency,'a','b'),['a','bridge','b'])
        self.assertIsNone(shortest_path(adjacency,'island','b'))
        self.assertEqual(shortest_path(adjacency,'a','a'),['a'])


if __name__=='__main__':
    unittest.main()
