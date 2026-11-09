"""Compare original polygon geometry with generated triangle coverage; never repair invalid faces."""
import json
from pathlib import Path
import numpy as np
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.placement
import ifcopenshell.util.unit
from polygon_geometry import face_analysis
from mesh_containment import mesh_integrity
from mesh_diagnostics import nearest_surface
from recover_fitting_interfaces import sha


def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'milestones/reproducibility'
    declaration_path=root/'architecture-declaration-audit.json'
    data=json.loads(declaration_path.read_text(encoding='utf-8'))
    models=[]
    for model in data['models']:
        path=project/'.dsh-state/architecture-cache/sources/ARCH/IFC'/model['source']
        if sha(path)!=model['source_sha256']:
            raise ValueError('Architecture source changed')
        print('Check original polygon coverage:',path.name,flush=True)
        source=ifcopenshell.open(str(path))
        scale=ifcopenshell.util.unit.calculate_unit_scale(source)
        settings=ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS,True)
        rooms=[]
        for space in model['native_spaces']:
            if space['name'] not in ('5202','5203') or 'Concrete_BuildingPermit_Revit' not in path.name:
                continue
            entity=source.by_id(space['ifc_id'])
            matrix=ifcopenshell.util.placement.get_local_placement(entity.ObjectPlacement)
            shape=ifcopenshell.geom.create_shape(settings,entity)
            generated_vertices=np.array(shape.geometry.verts).reshape(-1,3)
            generated_faces=np.array(shape.geometry.faces).reshape(-1,3)
            generated_triangles=generated_vertices[generated_faces]
            generated_area=np.linalg.norm(np.cross(generated_triangles[:,1]-generated_triangles[:,0],generated_triangles[:,2]-generated_triangles[:,0]),axis=1)/2
            items=[]
            for rep in entity.Representation.Representations:
                if rep.RepresentationIdentifier!='Body':
                    continue
                for item in rep.Items:
                    if not item.is_a('IfcPolygonalFaceSet') or item.PnIndex is not None:
                        raise ValueError('Unsupported native face input')
                    raw=np.array(item.Coordinates.CoordList)
                    vertices=(raw@matrix[:3,:3].T+matrix[:3,3])*scale
                    faces=[]
                    independent=[]
                    for index,face in enumerate(item.Faces):
                        indices=np.array(face.CoordIndex)-1
                        points=vertices[indices]
                        if face.is_a('IfcIndexedPolygonalFaceWithVoids'):
                            raise ValueError('Hole triangulation not assumed')
                        analysis=face_analysis(points)
                        if analysis['status']=='PLANAR_SIMPLE_TRIANGULATED':
                            independent.extend(indices[np.array(analysis['triangles'])].tolist())
                        faces.append({'face_index':index,'native_coordinate_indices':list(face.CoordIndex),'geometry_audit':analysis,
                            'points':points,'coverage_triangle_indices':[]})
                    ambiguous=[]
                    unmapped=[]
                    for triangle_index,triangle in enumerate(generated_triangles):
                        matches=[]
                        for face in faces:
                            analysis=face['geometry_audit']
                            if analysis['status']!='PLANAR_SIMPLE_TRIANGULATED':
                                continue
                            polygon=face['points']
                            _,_,axes=np.linalg.svd(polygon-polygon.mean(axis=0),full_matrices=False)
                            if np.abs((triangle-polygon.mean(axis=0))@axes[-1]).max()>1e-6:
                                continue
                            closest=nearest_surface(triangle.mean(axis=0),polygon,analysis['triangles'])
                            if closest['distance_m']<=1e-6:
                                matches.append(face['face_index'])
                        if len(matches)==1:
                            faces[matches[0]]['coverage_triangle_indices'].append(triangle_index)
                        elif matches:
                            ambiguous.append({'triangle':triangle_index,'native_faces':matches})
                        else:
                            unmapped.append(triangle_index)
                    output=[]
                    for face in faces:
                        coverage=float(generated_area[face['coverage_triangle_indices']].sum())
                        expected=face['geometry_audit'].get('triangulated_area_m2')
                        output.append({'face_index':face['face_index'],'native_coordinate_indices':face['native_coordinate_indices'],
                            'geometry_audit':face['geometry_audit'],'generated_covered_area_m2':coverage,
                            'coverage_residual_m2':coverage-expected if expected is not None else None,
                            'generated_triangles':face['coverage_triangle_indices']})
                    complete=all(f['geometry_audit']['status']=='PLANAR_SIMPLE_TRIANGULATED' for f in faces)
                    items.append({'item_id':item.id(),'declared_closed':item.Closed,'face_audits':output,
                        'ambiguous_generated_triangles':ambiguous,'unmapped_generated_triangles':unmapped,
                        'all_faces_planar_simple':complete,
                        'independent_mesh_integrity':mesh_integrity(vertices,np.array(independent)) if complete else None,
                        'generated_mesh_integrity':mesh_integrity(generated_vertices,generated_faces),
                        'native_vs_generated_bbox_max_gap_m':float(np.abs(np.array([vertices.min(axis=0),vertices.max(axis=0)])-np.array([generated_vertices.min(axis=0),generated_vertices.max(axis=0)])).max())})
            rooms.append({'ifc_id':entity.id(),'name':entity.Name,'long_name':entity.LongName,'items':items})
        del source
        if sha(path)!=model['source_sha256']:
            raise ValueError('Architecture modified during coverage audit')
        if rooms:
            models.append({'source':path.name,'source_sha256':model['source_sha256'],'rooms':rooms})
    invalid_count=sum(f['geometry_audit']['status']!='PLANAR_SIMPLE_TRIANGULATED' for m in models for r in m['rooms'] for i in r['items'] for f in i['face_audits'])
    result={'artifact_type':'native_polygon_planarity_and_generated_triangle_coverage','status':'FAIL_NATIVE_SIMPLE_FACE_GATE' if invalid_count else 'PASS_PLANAR_FACE_SCOPE_ONLY',
        'invalid_native_face_count':invalid_count,
        'inputHashes':{declaration_path.name:sha(declaration_path)},'codeSha256':sha(Path(__file__)),
        'polygonGeometryHelperSha256':sha(Path(__file__).with_name('polygon_geometry.py')),'meshHelperSha256':sha(Path(__file__).with_name('mesh_containment.py')),
        'diagnosticHelperSha256':sha(Path(__file__).with_name('mesh_diagnostics.py')),'models':models,
        'limitations':['Independent ear clipping is performed only for planar simple no-hole polygons; invalid input is not projected or repaired.',
            'Coverage attribution uses all triangle vertices coplanar and centroid in native face, with ambiguity retained.',
            'Closed independent mesh is not certification of cross-face self-intersection, room function, coordinate registration or installability.']}
    (root/'native-face-coverage-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps([{'source':m['source'],'rooms':[{'id':r['ifc_id'],'name':r['long_name'],'items':[{'all_faces_planar_simple':i['all_faces_planar_simple'],
        'independent_integrity':i['independent_mesh_integrity'],'generated_integrity':i['generated_mesh_integrity'],
        'bbox_gap_m':i['native_vs_generated_bbox_max_gap_m'],'ambiguous':i['ambiguous_generated_triangles'],'unmapped':i['unmapped_generated_triangles'],
        'faces':[{'face':f['face_index'],'status':f['geometry_audit']['status'],'planarity_m':f['geometry_audit'].get('plane_residual_m'),
            'crossings':f['geometry_audit'].get('intersection_details'),'covered_m2':f['generated_covered_area_m2'],'residual_m2':f['coverage_residual_m2']} for f in i['face_audits']]} for i in r['items']]} for r in m['rooms']]} for m in models],ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
