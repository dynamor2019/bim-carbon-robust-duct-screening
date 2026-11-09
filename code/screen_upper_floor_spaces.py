"""Upper-floor local-model bbox candidates only; no georeference or service certification."""
import json
from pathlib import Path
import numpy as np
import ifcopenshell
import ifcopenshell.geom
from recover_fitting_interfaces import sha
from mesh_containment import mesh_integrity,classify_point


def bbox_contains(point,lower,upper,tolerance=1e-6):
    point=np.asarray(point)
    return bool(np.all(point>=np.asarray(lower)-tolerance) and np.all(point<=np.asarray(upper)+tolerance))


def space_role(name):
    text=(name or '').upper()
    if text in ('GFA','GFA 250MM','HEATED NETAREA') or text.startswith('TURNING FREE SPACE'):
        return 'AGGREGATE_OR_ACCESSIBILITY_GEOMETRY'
    if text in ('CHASE','SHAFT'):
        return 'SHAFT_GEOMETRY'
    return 'NAMED_SPACE; function_label_not_service_certification'


def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'milestones/reproducibility'
    inventory_path=root/'architecture-space-inventory.json'
    inventory=json.loads(inventory_path.read_text(encoding='utf-8'))
    hashes={inventory_path.name:sha(inventory_path)}
    models=[]
    for architecture in inventory['architectural_models']:
        path=Path(architecture['source_path'])
        if sha(path)!=architecture['source_sha256']:
            raise ValueError('Architectural input changed')
        material='timber' if 'Timber' in path.name else 'concrete'
        interface_path=root/'network-interfaces'/(material+'-interfaces.json')
        hashes[interface_path.name]=sha(interface_path)
        data=json.loads(interface_path.read_text(encoding='utf-8'))
        targets=[record for record in data['components'] if (record['ifc_type']=='IfcAirTerminal' and record['psets'].get('FI_Sijainti',{}).get('Kerros')=='05_Kerros') or record['ifc_type']=='IfcFan']
        source=ifcopenshell.open(str(path))
        settings=ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS,True)
        spaces=[]
        meshes={}
        failures=[]
        for record in architecture['spaces']:
            if not any(parent['name']=='Level_05' for parent in record['parents']):
                continue
            try:
                shape=ifcopenshell.geom.create_shape(settings,source.by_id(record['ifc_id']))
                vertices=np.array(shape.geometry.verts).reshape(-1,3)
                if not len(vertices) or not np.isfinite(vertices).all():
                    raise ValueError('Empty/nonfinite space geometry')
                faces=np.array(shape.geometry.faces).reshape(-1,3)
                integrity=mesh_integrity(vertices,faces)
                meshes[record['ifc_id']]=(vertices,faces,integrity)
                spaces.append({'ifc_id':record['ifc_id'],'guid':record['guid'],'name':record['name'],'long_name':record['long_name'],
                    'role':space_role(record['long_name']),'mesh_integrity':integrity,'bbox_min_m':vertices.min(axis=0).tolist(),'bbox_max_m':vertices.max(axis=0).tolist()})
            except Exception as error:
                failures.append({'ifc_id':record['ifc_id'],'error':str(error)})
        del source
        if sha(path)!=architecture['source_sha256']:
            raise ValueError('Architectural input changed during geometry extraction')
        records=[]
        for target in targets:
            point=(np.array(target['bbox_min_m'])+np.array(target['bbox_max_m']))/2
            candidates=[space for space in spaces if bbox_contains(point,space['bbox_min_m'],space['bbox_max_m'])]
            xy=[space for space in spaces if bbox_contains(point[:2],space['bbox_min_m'][:2],space['bbox_max_m'][:2])]
            mesh_checks=[{'space_ifc_id':space['ifc_id'],'space_name':space['name'],'long_name':space['long_name'],
                'role':space['role'],**classify_point(point,*meshes[space['ifc_id']])} for space in candidates]
            records.append({'ifc_id':target['ifc_id'],'guid':target['guid'],'name':target['name'],'ifc_type':target['ifc_type'],
                'source_floor':target['psets'].get('FI_Sijainti',{}).get('Kerros'),'source_raw_flow':target['psets'].get('FI_Tekninen',{}).get('Virtaama'),
                'model_local_bbox_midpoint_m':point.tolist(),'full_3D_bbox_candidates':candidates,'XY_projection_candidates':xy,
                'mesh_point_checks':mesh_checks,
                'status':'LOCAL_MODEL_NUMERICAL_MESH_SCREEN_ONLY; frame_and_service_unverified'})
        models.append({'architecture_source':path.name,'source_sha256':architecture['source_sha256'],'hvac_model':data['model_id'],
            'space_geometry':spaces,'geometry_failures':failures,'target_records':records})
    result={'artifact_type':'upper_floor_local_model_spatial_candidates','status':'REQUIRES_FRAME_AND_CONTAINMENT_REVIEW',
        'inputHashes':hashes,'codeSha256':sha(Path(__file__)),'meshHelperSha256':sha(Path(__file__).with_name('mesh_containment.py')),'models':models,
        'limitations':['Geometry is model-local world coordinates in metres; no MapConversion applied or registration inferred.',
            'BBox containment can overinclude concave/overlapping spaces; aggregate/accessibility shapes are retained with flags.',
            'XY overlap is a separate weaker diagnostic, never treated as full 3D containment.',
            'A terminal bbox midpoint is a retrieval point, not a certified duct connector or functional room anchor.',
            'Numerical edge closure/orientation does not test self-intersections or vertex manifold links.',
            'Three-ray agreement with 1e-6 m hit merging is numerical evidence only; boundary/invalid/disagreement retained.',
            'No service assignment, root selection, demand exclusion or pressure model updated.']}
    (root/'upper-floor-spatial-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps([{'source':m['architecture_source'],'space_count':len(m['space_geometry']),'failures':m['geometry_failures'],
        'invalid_meshes':[{'id':s['ifc_id'],'name':s['long_name'],'integrity':s['mesh_integrity']} for s in m['space_geometry'] if s['mesh_integrity']['status']!='EDGE_CLOSED_ORIENTED'],
        'targets':[{'id':r['ifc_id'],'raw_flow':r['source_raw_flow'],'named_space_checks':[{k:c[k] for k in ('space_name','long_name','status')} for c in r['mesh_point_checks'] if c['role'].startswith('NAMED_SPACE')]} for r in m['target_records']]} for m in models],ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
