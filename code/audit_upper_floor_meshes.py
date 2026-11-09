"""Preserve partial mesh-gate failures and export disagreements; no source mesh repair."""
import json
from pathlib import Path
from collections import Counter,defaultdict
from recover_fitting_interfaces import sha


def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'milestones/reproducibility'
    path=root/'upper-floor-spatial-review.json'
    data=json.loads(path.read_text(encoding='utf-8'))
    models=[]
    failures=[]
    classifications=defaultdict(list)
    for model in data['models']:
        bad=[{'id':s['ifc_id'],'name':s['name'],'long_name':s['long_name'],'integrity':s['mesh_integrity']}
            for s in model['space_geometry'] if s['mesh_integrity']['status']!='EDGE_CLOSED_ORIENTED']
        models.append({'source':model['architecture_source'],'space_count':len(model['space_geometry']),
            'invalid_mesh_count':len(bad),'invalid_meshes':bad,
            'named_check_status_counts':dict(Counter(c['status'] for r in model['target_records'] for c in r['mesh_point_checks'] if c['role'].startswith('NAMED_SPACE')))})
        failures.extend({'source':model['architecture_source'],**s} for s in bad)
        for target in model['target_records']:
            checks={c['space_name']:c['status'] for c in target['mesh_point_checks'] if c['role'].startswith('NAMED_SPACE')}
            classifications[target['guid']].append({'source':model['architecture_source'],'ifc_id':target['ifc_id'],'checks':checks})
    disagreements=[]
    for guid,records in classifications.items():
        spaces=set().union(*(record['checks'] for record in records))
        for space in sorted(spaces):
            statuses=[record['checks'].get(space,'NOT_IN_3D_BBOX') for record in records]
            if len(set(statuses))>1:
                disagreements.append({'guid':guid,'space_name':space,'records':[{'source':r['source'],'ifc_id':r['ifc_id'],'status':status} for r,status in zip(records,statuses)]})
    result={'artifact_type':'upper_storey_source_mesh_gate','status':'FAIL_SOURCE_MESH_SCOPE' if failures else 'PASS_EDGE_CLOSURE_ONLY',
        'inputHashes':{path.name:sha(path)},'codeSha256':sha(Path(__file__)),'models':models,'failures':failures,
        'export_classification_disagreements':disagreements,
        'checks':[{'name':'all_selected_room_meshes_edge_closed_oriented','status':'FAIL' if failures else 'PASS','evidence':f'{len(failures)} selected space meshes fail'},
            {'name':'classification_consistent_across_exports','status':'FAIL' if disagreements else 'PASS','evidence':f'{len(disagreements)} paired space classification disagreements'}],
        'limitations':['Edge incidence failures may include nonconforming tessellation; not proof that native design has open room boundaries.',
            'No capping, coordinate shift, tolerance relaxation or favorable export selection applied.',
            'Mesh evidence remains model-local and does not certify room function, equipment service or installability.']}
    (root/'upper-floor-mesh-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps(result,ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
