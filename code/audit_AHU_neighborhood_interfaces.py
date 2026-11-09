"""AHU neighborhood across native 302/307/UI2/JI2 groups; numerical rims are not ports."""
import json
from pathlib import Path
from collections import Counter
import numpy as np
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.unit
import ifcopenshell.util.element
from extract_network_interfaces import extract_entity,match_features
from trace_source_boundary import group_memberships,simple
from recover_fitting_interfaces import sha


def bbox_gap(a_min,a_max,b_min,b_max):
    return float(np.linalg.norm(np.maximum(np.maximum(np.array(a_min)-b_max,np.array(b_min)-a_max),0)))


def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'milestones/reproducibility'
    inputs={}
    sources=[]
    models=[]
    for material,fan_id in (('Concrete',3305376),('Timber',3912298)):
        model=f'HVAC_NordicLCA_Office_{material}_BuildingPermit'
        inventory_path=root/'network-interfaces'/f'{material.lower()}-interfaces.json'
        inventory=json.loads(inventory_path.read_text(encoding='utf-8'))
        inputs['network-interfaces/'+inventory_path.name]=sha(inventory_path)
        path=project.parent/'extracted/HVAC/IFC'/(model+'.ifc')
        expected=inventory['sourceSha256']
        if sha(path)!=expected:
            raise ValueError('Source changed')
        sources.append({'path':str(path),'sha256':expected})
        print('AHU native-group neighborhood:',material,flush=True)
        source=ifcopenshell.open(str(path))
        fan=source.by_id(fan_id)
        memberships=group_memberships(fan)
        group_ids={g['group_id'] for g in memberships}
        members={e.id():e for gid in group_ids for rel in source.by_id(gid).IsGroupedBy for e in rel.RelatedObjects}
        cached={r['ifc_id']:r for r in inventory['components']}
        fan_record=cached[fan_id]
        fan_min=np.array(fan_record['bbox_min_m'])
        fan_max=np.array(fan_record['bbox_max_m'])
        settings=ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS,True)
        scale=ifcopenshell.util.unit.calculate_unit_scale(source)
        cache=project/'.dsh-state/AHU-neighborhood-cache'/model
        cache.mkdir(parents=True,exist_ok=True)
        records=[]
        failures=[]
        meshes=[]
        for entity in sorted(members.values(),key=lambda e:e.id()):
            if not entity.is_a('IfcProduct') or not entity.Representation:
                continue
            record=cached.get(entity.id())
            if record and record.get('bbox_min_m') is not None:
                if sha(Path(record['mesh_path']))!=record['mesh_sha256']:
                    raise ValueError('Cached mesh hash changed')
            else:
                try:
                    record=extract_entity(entity,settings,scale,cache/str(entity.id()),'raw-source-ahU-neighborhood-'+expected)
                except Exception as error:
                    failures.append({'id':entity.id(),'name':entity.Name,'type':entity.is_a(),'error':repr(error)})
                    continue
            gap=bbox_gap(fan_min,fan_max,np.array(record['bbox_min_m']),np.array(record['bbox_max_m']))
            if gap>1.0 and entity.id()!=fan_id:
                continue
            meshes.append({'path':record['mesh_path'],'sha256':record['mesh_sha256']})
            psets=simple(ifcopenshell.util.element.get_psets(entity))
            records.append({'ifc_id':entity.id(),'guid':entity.GlobalId,'type':entity.is_a(),'name':entity.Name,
                'groups':group_memberships(entity),'device_code':psets.get('FI_Komponentti',{}).get('Laitetunnus'),
                'psets':psets,'bbox_gap_to_AHU_m':gap,'bbox_min_m':record['bbox_min_m'],'bbox_max_m':record['bbox_max_m'],
                'feature_method':record['method'],'candidate_features':record['features']})
        ports=[dict(feature,ifc_id=r['ifc_id'],port_id=f"{r['ifc_id']}:{i}") for r in records for i,feature in enumerate(r['candidate_features'])]
        matches=match_features(ports)
        fan_matches=[m for m in matches if fan_id in (m['ifc_a'],m['ifc_b'])]
        degree=Counter(p for m in fan_matches for p in (m['port_a'],m['port_b']))
        fan_features=[dict(p,matching_candidate_count=degree[p['port_id']]) for p in ports if p['ifc_id']==fan_id]
        native_counts={kind:len(source.by_type(kind)) for kind in ('IfcDistributionPort','IfcRelConnectsPorts','IfcRelConnectsPortToElement')}
        del source
        if sha(path)!=expected:
            raise ValueError('Source changed')
        models.append({'source':model+'.ifc','fan_id':fan_id,'native_groups':memberships,'group_union_member_count':len(members),
            'scope_bbox_separation_m':1.,'scope_note':'Screening extent only; not joint tolerance or installation clearance.',
            'extraction_failures':failures,'native_connectivity_entity_counts':native_counts,'records':records,
            'fan_candidate_features':fan_features,'fan_candidate_matches':fan_matches,'neighborhood_candidate_matches':matches,'cached_mesh_inputs':meshes})
    report={'artifact_type':'native_multisystem_AHU_neighborhood_circular_interface_diagnosis','status':'AHU_BOUNDARY_UNCERTIFIED',
        'inputHashes':inputs,'source_files':sources,'codeSha256':sha(Path(__file__)),
        'helperHashes':{name:sha(Path(__file__).with_name(name)) for name in ('extract_network_interfaces.py','verify_paired_boundary.py','recover_fitting_interfaces.py','trace_source_boundary.py')},
        'models':models,'limitations':['Circular rim near-equality alone is not a native port, flow direction or approved physical connection.',
            'Rectangular or unsupported AHU interfaces remain outside this circular matching scope; absence of matches is not physical isolation.',
            'All numerical ambiguities and geometry extraction failures retained; screening extent does not decide service.',
            'No 302/307 demand moved and no fan-performance parameter assigned.']}
    (root/'AHU-neighborhood-interface-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':report['status'],'models':[{'source':m['source'],'members':m['group_union_member_count'],'near_records':len(m['records']),
        'failures':len(m['extraction_failures']),'native_counts':m['native_connectivity_entity_counts'],'fan_features':m['fan_candidate_features'],'fan_matches':m['fan_candidate_matches'],
        'near_components':[{'id':r['ifc_id'],'name':r['name'],'type':r['type'],'raw_flow':r['psets'].get('FI_Tekninen',{}).get('Virtaama'),
            'bbox_gap_m':r['bbox_gap_to_AHU_m'],'groups':[g['group_name'] for g in r['groups']]} for r in m['records']]} for m in models]},ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
