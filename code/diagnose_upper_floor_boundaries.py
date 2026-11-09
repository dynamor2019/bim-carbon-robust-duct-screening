"""Reopen original room representations to diagnose edge failures and sauna boundary offsets."""
import json
from pathlib import Path
import numpy as np
import ifcopenshell
import ifcopenshell.geom
from mesh_containment import mesh_integrity,classify_point
from mesh_diagnostics import edge_subdivision_audit,nearest_surface
from recover_rectangular_interfaces import mesh
from recover_fitting_interfaces import sha


def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'milestones/reproducibility'
    spatial_path=root/'upper-floor-spatial-review.json'
    data=json.loads(spatial_path.read_text(encoding='utf-8'))
    hashes={spatial_path.name:sha(spatial_path)}
    reports=[]
    for model in data['models']:
        material='timber' if 'Timber' in model['architecture_source'] else 'concrete'
        inventory_path=root/'network-interfaces'/(material+'-interfaces.json')
        hashes[inventory_path.name]=sha(inventory_path)
        inventory=json.loads(inventory_path.read_text(encoding='utf-8'))
        components={r['ifc_id']:r for r in inventory['components']}
        path=project/'.dsh-state/architecture-cache/sources/ARCH/IFC'/model['architecture_source']
        if sha(path)!=model['source_sha256']:
            raise ValueError('Original architecture changed')
        print('Diagnose original room:',path.name,flush=True)
        source=ifcopenshell.open(str(path))
        settings=ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS,True)
        rooms=[]
        for record in model['space_geometry']:
            if record['mesh_integrity']['status']=='EDGE_CLOSED_ORIENTED' and record['name']!='5205':
                continue
            entity=source.by_id(record['ifc_id'])
            representation=[{'identifier':rep.RepresentationIdentifier,'representation_type':rep.RepresentationType,
                'item_types':[item.is_a() for item in rep.Items]} for rep in entity.Representation.Representations]
            shape=ifcopenshell.geom.create_shape(settings,entity)
            vertices=np.array(shape.geometry.verts).reshape(-1,3)
            faces=np.array(shape.geometry.faces).reshape(-1,3)
            integrity=mesh_integrity(vertices,faces)
            edge_audit=edge_subdivision_audit(vertices,faces)
            point_records=[]
            if record['name']=='5205':
                for target in model['target_records']:
                    if not any(c['space_name']=='5205' for c in target['mesh_point_checks']):
                        continue
                    point=target['model_local_bbox_midpoint_m']
                    closest=nearest_surface(point,vertices,faces)
                    terminal=components[target['ifc_id']]
                    terminal_vertices,_=mesh(terminal)
                    checks=[classify_point(p,vertices,faces,integrity) for p in terminal_vertices]
                    counts={status:sum(c['status']==status for c in checks) for status in sorted({c['status'] for c in checks})}
                    nearest_point=np.array(closest['closest_point_m'])
                    normal=np.array(closest['face_normal'])
                    signed=(terminal_vertices-nearest_point)@normal
                    point_records.append({'terminal_ifc_id':target['ifc_id'],'guid':target['guid'],'raw_flow':target['source_raw_flow'],
                        'midpoint':point,'midpoint_classification':classify_point(point,vertices,faces,integrity),
                        'nearest_surface':closest,'cached_terminal_mesh_sha256':terminal['mesh_sha256'],
                        'terminal_vertex_status_counts':counts,'nearest_triangle_plane_signed_span_m':[float(signed.min()),float(signed.max())],
                        'terminal_mesh_bbox_min_m':terminal_vertices.min(axis=0).tolist(),'terminal_mesh_bbox_max_m':terminal_vertices.max(axis=0).tolist()})
            rooms.append({'ifc_id':record['ifc_id'],'name':record['name'],'long_name':record['long_name'],
                'native_representation':representation,'raw_mesh_integrity':integrity,'edge_subdivision_diagnostic':edge_audit,'terminal_boundary_checks':point_records})
        del source
        if sha(path)!=model['source_sha256']:
            raise ValueError('Architecture source changed')
        reports.append({'source':model['architecture_source'],'source_sha256':model['source_sha256'],'rooms':rooms})
    result={'artifact_type':'original_space_boundary_failure_diagnosis','status':'DIAGNOSIS_ONLY; SOURCE_GATE_NOT_OVERRIDDEN',
        'inputHashes':hashes,'codeSha256':sha(Path(__file__)),'meshHelperSha256':sha(Path(__file__).with_name('mesh_containment.py')),
        'diagnosticHelperSha256':sha(Path(__file__).with_name('mesh_diagnostics.py')),'models':reports,
        'limitations':['Existing collinear vertices refine edge incidence bookkeeping only; no input geometry modified.',
            'Nearest-surface and sampled vertex tests do not choose a replacement room anchor or prove service direction.',
            'Registration, self-intersections and vertex manifold links remain unverified.',
            'Old raw mesh failures and contradictory exports remain in validation history.']}
    (root/'upper-floor-boundary-diagnosis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps([{'source':m['source'],'rooms':[{'id':r['ifc_id'],'name':r['long_name'],'representation':r['native_representation'],
        'raw_bad_edges':r['edge_subdivision_diagnostic']['raw_non_two_incident_edges'],
        'subdivided_bad_segments':r['edge_subdivision_diagnostic']['subdivided_non_two_incident_segments'],
        'subdivided_bad_winding':r['edge_subdivision_diagnostic']['subdivided_inconsistent_winding'],
        'terminal_checks':r['terminal_boundary_checks']} for r in m['rooms']]} for m in reports],ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
