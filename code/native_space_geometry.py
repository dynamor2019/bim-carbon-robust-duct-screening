"""Read native room polygons and supported straight-sided extrusion profiles without repair."""
import numpy as np
import ifcopenshell.util.placement
from polygon_geometry import face_analysis
from polygon_holes import hole_audit


def curve_points(curve,scale):
    if curve.is_a('IfcPolyline'):
        points=np.array([p.Coordinates for p in curve.Points],float)*scale
    elif curve.is_a('IfcIndexedPolyCurve'):
        points=np.array(curve.Points.CoordList,float)*scale
        if curve.Segments:
            path=[]
            for segment in curve.Segments:
                if not segment.is_a('IfcLineIndex'):
                    return None,'UNSUPPORTED_CURVED_SEGMENT'
                indices=list(segment.wrappedValue)
                if path and path[-1]!=indices[0]:
                    return None,'DISCONNECTED_PROFILE_SEGMENTS'
                path.extend(indices if not path else indices[1:])
            points=points[np.array(path)-1]
    else:
        return None,'UNSUPPORTED_PROFILE_CURVE'
    if np.linalg.norm(points[0]-points[-1])>1e-8:
        return None,'PROFILE_LOOP_NOT_EXPLICITLY_CLOSED'
    return points[:-1],'SUPPORTED_CLOSED_STRAIGHT_PROFILE'


def profile_audit(profile,scale):
    if profile.is_a('IfcArbitraryProfileDefWithVoids'):
        outer,status=curve_points(profile.OuterCurve,scale)
        if outer is None:
            return {'status':status,'profile_type':profile.is_a()}
        holes=[]
        for curve in profile.InnerCurves:
            points,status=curve_points(curve,scale)
            if points is None:
                return {'status':status,'profile_type':profile.is_a()}
            holes.append(np.column_stack([points[:,:2],np.zeros(len(points))]))
        audit=hole_audit(np.column_stack([outer[:,:2],np.zeros(len(outer))]),holes)
        return {'status':'SUPPORTED_PROFILE' if audit['status']=='PASS_HOLE_RING_SCOPE' else 'INVALID_PROFILE',
            'profile_type':profile.is_a(),'geometry_audit':audit}
    if profile.is_a('IfcRectangleProfileDef'):
        if profile.XDim<=0 or profile.YDim<=0:
            return {'status':'INVALID_PROFILE','profile_type':profile.is_a(),'reason':'NONPOSITIVE_RECTANGLE_DIMENSION'}
        x,y=profile.XDim*scale/2,profile.YDim*scale/2
        points=np.array([[-x,-y],[x,-y],[x,y],[-x,y]])
        declaration='PARAMETRIC_RECTANGLE'
    elif profile.is_a('IfcArbitraryClosedProfileDef') and not profile.is_a('IfcArbitraryProfileDefWithVoids'):
        points,declaration=curve_points(profile.OuterCurve,scale)
        if points is None:
            return {'status':declaration,'profile_type':profile.is_a()}
    else:
        return {'status':'UNSUPPORTED_PROFILE_TYPE','profile_type':profile.is_a()}
    points3=np.column_stack([points[:,:2],np.zeros(len(points))])
    audit=face_analysis(points3)
    return {'status':'SUPPORTED_PROFILE' if audit['status']=='PLANAR_SIMPLE_TRIANGULATED' else 'INVALID_PROFILE',
        'profile_type':profile.is_a(),'loop_declaration':declaration,'geometry_audit':audit}


def item_audit(item,object_matrix,scale):
    if item.is_a('IfcPolygonalFaceSet'):
        if item.PnIndex is not None:
            return {'type':item.is_a(),'status':'UNSUPPORTED_PNINDEX'}
        vertices=(np.array(item.Coordinates.CoordList)@object_matrix[:3,:3].T+object_matrix[:3,3])*scale
        faces=[]
        unsupported=0
        for index,face in enumerate(item.Faces):
            if face.is_a('IfcIndexedPolygonalFaceWithVoids'):
                outer=vertices[np.array(face.CoordIndex)-1]
                holes=[vertices[np.array(indices)-1] for indices in face.InnerCoordIndices]
                audit=hole_audit(outer,holes)
                faces.append({'face_index':index,'status':audit['status'],'geometry_audit':audit})
                continue
            audit=face_analysis(vertices[np.array(face.CoordIndex)-1])
            faces.append({'face_index':index,'status':audit['status'],'geometry_audit':audit})
        invalid=sum(f['status'] not in ('PLANAR_SIMPLE_TRIANGULATED','PASS_HOLE_RING_SCOPE') for f in faces)
        return {'type':item.is_a(),'status':'INVALID_NATIVE_FACE' if invalid else 'UNSUPPORTED_INNER_LOOPS' if unsupported else 'PASS_PLANAR_SIMPLE_FACE_SCOPE',
            'declared_closed':item.Closed,'invalid_faces':invalid,'unsupported_faces':unsupported,'faces':faces}
    if item.is_a('IfcExtrudedAreaSolid'):
        audit=profile_audit(item.SweptArea,scale)
        direction=np.array(item.ExtrudedDirection.DirectionRatios,float)
        valid=bool(item.Depth>0 and np.isfinite(direction).all() and np.linalg.norm(direction)>0 and abs(direction[2])>1e-12)
        return {'type':item.is_a(),'status':'INVALID_EXTRUSION' if not valid else 'INVALID_PROFILE' if audit['status']=='INVALID_PROFILE' else 'PASS_EXTRUSION_PROFILE_SCOPE' if audit['status']=='SUPPORTED_PROFILE' else 'UNSUPPORTED_EXTRUSION_PROFILE',
            'depth_m':float(item.Depth*scale),'extruded_direction_ratios':direction.tolist(),'profile_audit':audit,
            'limitations':['Profile validity and positive depth are not a closed-solid or placement-registration certification.']}
    return {'type':item.is_a(),'status':'UNSUPPORTED_NATIVE_BODY_ITEM'}
