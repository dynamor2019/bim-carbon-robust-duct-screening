"""Compare native hole-domain areas/void-extrusion volume against raw generated meshes."""
import json
from pathlib import Path
import numpy as np
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.unit
import ifcopenshell.util.placement
from native_space_geometry import profile_audit
from polygon_holes import hole_audit,point_in_ring
from mesh_containment import mesh_integrity
from recover_fitting_interfaces import sha


def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'milestones/reproducibility'
    path=root/'upper-floor-spatial-review.json'
    data=json.loads(path.read_text(encoding='utf-8'))
    models=[]
    failed=0
    for model in data['models']:
        source_path=project/'.dsh-state/architecture-cache/sources/ARCH/IFC'/model['architecture_source']
        if sha(source_path)!=model['source_sha256']:
            raise ValueError('Architecture source changed')
        print('Check hole domain coverage:',source_path.name,flush=True)
        source=ifcopenshell.open(str(source_path))
        scale=ifcopenshell.util.unit.calculate_unit_scale(source)
        settings=ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS,True)
        spaces=[]
        for space in model['space_geometry']:
            entity=source.by_id(space['ifc_id'])
            items=[item for rep in entity.Representation.Representations if rep.RepresentationIdentifier=='Body' for item in rep.Items]
            selected=[i for i in items if (i.is_a('IfcPolygonalFaceSet') and any(f.is_a('IfcIndexedPolygonalFaceWithVoids') for f in i.Faces)) or (i.is_a('IfcExtrudedAreaSolid') and i.SweptArea.is_a('IfcArbitraryProfileDefWithVoids'))]
            if not selected:
                continue
            shape=ifcopenshell.geom.create_shape(settings,entity)
            vertices=np.array(shape.geometry.verts).reshape(-1,3)
            faces=np.array(shape.geometry.faces).reshape(-1,3)
            integrity=mesh_integrity(vertices,faces)
            triangles=vertices[faces]
            areas=np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1)/2
            matrix=ifcopenshell.util.placement.get_local_placement(entity.ObjectPlacement)
            checks=[]
            for item in selected:
                if item.is_a('IfcPolygonalFaceSet'):
                    if item.PnIndex is not None:
                        raise ValueError('Unsupported polygon point mapping')
                    points=(np.array(item.Coordinates.CoordList)@matrix[:3,:3].T+matrix[:3,3])*scale
                    for index,face in enumerate(item.Faces):
                        if not face.is_a('IfcIndexedPolygonalFaceWithVoids'):
                            continue
                        outer=points[np.array(face.CoordIndex)-1]
                        holes=[points[np.array(h)-1] for h in face.InnerCoordIndices]
                        audit=hole_audit(outer,holes)
                        if audit['status']!='PASS_HOLE_RING_SCOPE':
                            checks.append({'face_index':index,'status':'FAIL_RING_DOMAIN','ring_audit':audit})
                            continue
                        origin=outer.mean(axis=0)
                        _,_,axes=np.linalg.svd(outer-origin,full_matrices=False)
                        projected=[np.column_stack([(r-origin)@axes[0],(r-origin)@axes[1]]) for r in [outer]+holes]
                        matching=[]
                        hole_centroid_triangles=[]
                        for k,triangle in enumerate(triangles):
                            if np.abs((triangle-origin)@axes[-1]).max()>1e-6:
                                continue
                            centre=triangle.mean(axis=0)-origin
                            point=np.array([centre@axes[0],centre@axes[1]])
                            if point_in_ring(point,projected[0])=='OUTSIDE':
                                continue
                            if any(point_in_ring(point,h)!='OUTSIDE' for h in projected[1:]):
                                hole_centroid_triangles.append(k)
                            else:
                                matching.append(k)
                        covered=float(areas[matching].sum())
                        tolerance=max(1e-7,1e-7*audit['net_area_m2'])
                        residual=covered-audit['net_area_m2']
                        status='PASS_AGGREGATE_AREA_SCOPE' if abs(residual)<=tolerance and not hole_centroid_triangles else 'FAIL_AGGREGATE_AREA_SCOPE'
                        checks.append({'face_index':index,'status':status,'ring_audit':audit,'generated_area_m2':covered,
                            'area_residual_m2':residual,'area_tolerance_m2':tolerance,
                            'triangles_with_centroid_in_hole':hole_centroid_triangles,'matching_triangle_count':len(matching)})
                else:
                    audit=profile_audit(item.SweptArea,scale)
                    if audit['status']!='SUPPORTED_PROFILE':
                        checks.append({'item_id':item.id(),'status':'FAIL_PROFILE_DOMAIN','profile_audit':audit})
                        continue
                    direction=np.array(item.ExtrudedDirection.DirectionRatios)
                    expected=audit['geometry_audit']['net_area_m2']*item.Depth*scale*abs(direction[2])/np.linalg.norm(direction)
                    actual=abs(integrity['signed_volume_m3'])
                    tolerance=max(1e-6,1e-6*expected)
                    status='PASS_EXTRUSION_VOLUME_SCOPE' if integrity['status']=='EDGE_CLOSED_ORIENTED' and abs(actual-expected)<=tolerance and len(items)==1 else 'FAIL_EXTRUSION_VOLUME_SCOPE'
                    checks.append({'item_id':item.id(),'status':status,'profile_audit':audit,'native_volume_m3':float(expected),
                        'generated_volume_m3':actual,'volume_residual_m3':float(actual-expected),'volume_tolerance_m3':float(tolerance)})
            pass_space=bool(checks) and all(c['status'].startswith('PASS') for c in checks)
            failed+=int(not pass_space)
            spaces.append({'ifc_id':space['ifc_id'],'name':space['name'],'long_name':space['long_name'],'role':space['role'],
                'status':'PASS_HOLE_COVERAGE_SCOPE_ONLY' if pass_space else 'FAIL_HOLE_COVERAGE_SCOPE','generated_mesh_integrity':integrity,'checks':checks})
        del source
        if sha(source_path)!=model['source_sha256']:
            raise ValueError('Source changed')
        models.append({'source':source_path.name,'source_sha256':model['source_sha256'],'spaces':spaces})
    report={'artifact_type':'upper_storey_hole_ring_area_and_extrusion_volume_check','status':'FAIL_HOLE_COVERAGE_SCOPE' if failed else 'PASS_HOLE_COVERAGE_SCOPE_ONLY',
        'failed_space_count':failed,'inputHashes':{path.name:sha(path)},'codeSha256':sha(Path(__file__)),
        'nativeSpaceHelperSha256':sha(Path(__file__).with_name('native_space_geometry.py')),'polygonHolesHelperSha256':sha(Path(__file__).with_name('polygon_holes.py')),
        'polygonGeometryHelperSha256':sha(Path(__file__).with_name('polygon_geometry.py')),'meshHelperSha256':sha(Path(__file__).with_name('mesh_containment.py')),
        'models':models,'limitations':['Area sums and triangle centroids do not certify complete coverage or exclude compensating overlap/gaps.',
            'Extrusion volume agreement uses original hole-subtracted area, positive depth and generated oriented edge closure; no physical service certification.',
            'Cross-face intersection, registration and installation clearances are not checked; old proper-crossing source failures remain.']}
    (root/'upper-storey-hole-coverage-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':report['status'],'models':[{'source':m['source'],'spaces':[{'id':s['ifc_id'],'name':s['long_name'],'status':s['status'],
        'checks':[{k:v for k,v in c.items() if k not in ('ring_audit','profile_audit')} for c in s['checks']]} for s in m['spaces']]} for m in models]},ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
