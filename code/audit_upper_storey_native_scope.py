"""Expand native face/profile gate to all three exports' upper-storey spaces."""
import json
from collections import Counter
from pathlib import Path
import ifcopenshell
import ifcopenshell.util.placement
import ifcopenshell.util.unit
from native_space_geometry import item_audit
from recover_fitting_interfaces import sha


def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'milestones/reproducibility'
    path=root/'upper-floor-spatial-review.json'
    data=json.loads(path.read_text(encoding='utf-8'))
    models=[]
    invalid_total=unsupported_total=0
    for model in data['models']:
        source_path=project/'.dsh-state/architecture-cache/sources/ARCH/IFC'/model['architecture_source']
        if sha(source_path)!=model['source_sha256']:
            raise ValueError('Original architecture changed')
        print('Audit full upper-storey scope:',source_path.name,flush=True)
        source=ifcopenshell.open(str(source_path))
        scale=ifcopenshell.util.unit.calculate_unit_scale(source)
        spaces=[]
        for record in model['space_geometry']:
            entity=source.by_id(record['ifc_id'])
            matrix=ifcopenshell.util.placement.get_local_placement(entity.ObjectPlacement)
            items=[]
            if entity.Representation:
                for representation in entity.Representation.Representations:
                    if representation.RepresentationIdentifier=='Body':
                        items.extend(item_audit(item,matrix,scale) for item in representation.Items)
            invalid=any(item['status'].startswith('INVALID') for item in items)
            unsupported=not items or any(item['status'].startswith('UNSUPPORTED') for item in items)
            status='FAIL_NATIVE_GEOMETRY' if invalid else 'NOT_FULLY_SUPPORTED' if unsupported else 'PASS_FACE_PROFILE_SCOPE_ONLY'
            invalid_total+=int(invalid)
            unsupported_total+=int(unsupported)
            affected=[]
            for target in model['target_records']:
                full=any(s['ifc_id']==record['ifc_id'] for s in target['full_3D_bbox_candidates'])
                xy=any(s['ifc_id']==record['ifc_id'] for s in target['XY_projection_candidates'])
                if full or xy:
                    affected.append({'target_ifc_id':target['ifc_id'],'guid':target['guid'],'raw_flow':target['source_raw_flow'],
                        'candidate_basis':'FULL_3D_BBOX' if full else 'XY_ONLY',
                        'numerical_mesh_status':[c['status'] for c in target['mesh_point_checks'] if c['space_ifc_id']==record['ifc_id']]})
            spaces.append({'ifc_id':record['ifc_id'],'guid':record['guid'],'name':record['name'],'long_name':record['long_name'],
                'role':record['role'],'status':status,'native_body_audits':items,'bbox_candidate_targets':affected})
        del source
        if sha(source_path)!=model['source_sha256']:
            raise ValueError('Source changed during native audit')
        models.append({'source':source_path.name,'source_sha256':model['source_sha256'],'space_count':len(spaces),
            'scope_status_counts':dict(Counter(s['status'] for s in spaces)),
            'body_item_type_counts':dict(Counter(i['type'] for s in spaces for i in s['native_body_audits'])),
            'spaces':spaces})
    report={'artifact_type':'all_upper_storey_native_space_geometry_scope','status':'FAIL_NATIVE_GEOMETRY_SCOPE' if invalid_total else 'INCOMPLETE_NATIVE_GEOMETRY_SCOPE' if unsupported_total else 'PASS_FACE_PROFILE_SCOPE_ONLY',
        'invalid_space_count':invalid_total,'unsupported_space_count':unsupported_total,
        'inputHashes':{path.name:sha(path)},'codeSha256':sha(Path(__file__)),
        'nativeSpaceHelperSha256':sha(Path(__file__).with_name('native_space_geometry.py')),
        'polygonHolesHelperSha256':sha(Path(__file__).with_name('polygon_holes.py')),
        'polygonGeometryHelperSha256':sha(Path(__file__).with_name('polygon_geometry.py')),'models':models,
        'limitations':['All upper-storey spaces already successfully extracted are included; other storeys and construction obstacles are outside scope.',
            'Face/profile validity is not volume containment, cross-face intersection, placement registration or physical service certification.',
            'Candidate impact counts retain overlapping and XY-only associations; no terminal demand is excluded or reassigned.',
            'Unsupported types and curved contours are not silently tessellated, filled or treated as valid; supported hole rings are checked without filling.']}
    (root/'upper-storey-native-scope-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':report['status'],'invalid_spaces':invalid_total,'unsupported_spaces':unsupported_total,
        'models':[{'source':m['source'],'space_count':m['space_count'],'status_counts':m['scope_status_counts'],'types':m['body_item_type_counts'],
            'nonpassing_spaces':[{k:s[k] for k in ('ifc_id','name','long_name','role','status','bbox_candidate_targets')} for s in m['spaces'] if s['status']!='PASS_FACE_PROFILE_SCOPE_ONLY']} for m in models]},ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
