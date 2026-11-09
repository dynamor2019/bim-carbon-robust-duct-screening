"""Extract all native 302 group members' candidate circular geometric interfaces.
Read-only IFC source audit, not formal routing/sizing optimization.
"""
import hashlib
import itertools
import json
import math
from collections import Counter,defaultdict
from pathlib import Path
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import ifcopenshell.util.unit
import numpy as np
from verify_paired_boundary import extrusion_axes,sha
from recover_fitting_interfaces import recover_rims

SYSTEM='302PK01 (toimistot, oikea)'
CENTER_TOL=1e-5
RADIUS_TOL=1e-5
ANGLE_TOL_DEG=.01


def group_features(features):
    groups=[]
    for feature in features:
        center=np.array(feature['center_m'])
        normal=np.array(feature['normal_sign_arbitrary'])
        for group in groups:
            if np.linalg.norm(center-np.array(group['center_m']))<=1e-6 and abs(normal@np.array(group['normal_sign_arbitrary']))>=math.cos(math.radians(ANGLE_TOL_DEG)):
                group['radii_m']=sorted(set(group['radii_m']+[feature['radius_m']]))
                group['origins'].append(feature['origin'])
                break
        else:
            groups.append({'center_m':center.tolist(),'normal_sign_arbitrary':normal.tolist(),
                           'radii_m':[feature['radius_m']],'origins':[feature['origin']]})
    return groups


def match_features(ports):
    grid=defaultdict(list)
    pairs=[]
    for i,port in enumerate(ports):
        center=np.array(port['center_m'])
        cell=tuple(np.floor(center/CENTER_TOL).astype(np.int64).tolist())
        for offset in itertools.product((-1,0,1),repeat=3):
            for j in grid.get(tuple(cell[k]+offset[k] for k in range(3)),()):
                other=ports[j]
                if port['ifc_id']==other['ifc_id']:
                    continue
                gap=float(np.linalg.norm(center-np.array(other['center_m'])))
                if gap>CENTER_TOL:
                    continue
                cosine=float(np.clip(abs(np.array(port['normal_sign_arbitrary'])@np.array(other['normal_sign_arbitrary'])),0,1))
                angle=math.degrees(math.acos(cosine))
                radius_gap=min(abs(a-b) for a in port['radii_m'] for b in other['radii_m'])
                if angle<=ANGLE_TOL_DEG and radius_gap<=RADIUS_TOL:
                    pairs.append({'port_a':other['port_id'],'port_b':port['port_id'],
                        'ifc_a':other['ifc_id'],'ifc_b':port['ifc_id'],
                        'center_gap_m':gap,'axis_normal_angle_deg':angle,'radius_gap_m':radius_gap,
                        'status':'NUMERIC_FEATURE_MATCH_ONLY; service_and_flow_unverified'})
        grid[cell].append(i)
    return pairs


def extract_entity(entity,settings,scale,cache_path,signature):
    shape=ifcopenshell.geom.create_shape(settings,entity)
    vertices=np.asarray(shape.geometry.verts,dtype=float).reshape(-1,3)
    faces=np.asarray(shape.geometry.faces,dtype=np.int64).reshape(-1,3)
    if not len(vertices) or not len(faces) or not np.isfinite(vertices).all():
        raise ValueError('empty or nonfinite mesh')
    mesh_path=cache_path.with_suffix('.npz')
    np.savez_compressed(mesh_path,vertices=vertices,faces=faces)
    features=[]
    axes=[]
    method='mesh_circular_rims'
    mesh_review=None
    if entity.is_a('IfcDuctSegment'):
        axes=extrusion_axes(entity,scale)
        for axis in axes:
            if axis['source_outer_radius_m'] is None or axis['axis_length_m']<=1e-10:
                continue
            ends=np.array([axis['end_a_m'],axis['end_b_m']])
            outside=np.maximum(np.maximum(vertices.min(axis=0)-ends,ends-vertices.max(axis=0)),0)
            if outside.max()>1e-6:
                raise ValueError('original extrusion axis endpoint outside world mesh bbox')
            direction=(ends[1]-ends[0])/np.linalg.norm(ends[1]-ends[0])
            for label,point in [('a',ends[0]),('b',ends[1])]:
                features.append({'center_m':point.tolist(),'normal_sign_arbitrary':direction.tolist(),
                    'radius_m':axis['source_outer_radius_m'],'origin':'original_extrusion_axis_end_'+label})
        if features:
            method='source_circular_extrusion'
    if not features:
        mesh_review=recover_rims(vertices,faces)
        features=mesh_review['rims']
    psets=ifcopenshell.util.element.get_psets(entity)
    record={'cache_signature':signature,'ifc_id':entity.id(),'guid':entity.GlobalId,'ifc_type':entity.is_a(),
        'name':entity.Name,'psets':psets,'bbox_min_m':vertices.min(axis=0).tolist(),
        'bbox_max_m':vertices.max(axis=0).tolist(),'mesh_sha256':sha(mesh_path),'mesh_path':str(mesh_path),
        'method':method,'features':group_features(features),'axes':axes,'mesh_review':mesh_review,
        'status':'CANDIDATE_FEATURES_ONLY' if features else 'NO_SUPPORTED_CIRCULAR_FEATURES',
        'evidence_limit':'Geometric rims may include covers/decorative rings; source semantic service, native connectivity and flow direction not certified.'}
    return record


def summarize(model,records,ports,pairs):
    degree=Counter(p for edge in pairs for p in [edge['port_a'],edge['port_b']])
    adjacency={r['ifc_id']:set() for r in records}
    for edge in pairs:
        adjacency[edge['ifc_a']].add(edge['ifc_b'])
        adjacency[edge['ifc_b']].add(edge['ifc_a'])
    remaining=set(adjacency)
    groups=[]
    by_id={r['ifc_id']:r for r in records}
    while remaining:
        todo=[min(remaining)]
        visited=set()
        while todo:
            node=todo.pop()
            if node in visited:
                continue
            visited.add(node)
            todo.extend(adjacency[node]-visited)
        remaining-=visited
        terminals=[by_id[n] for n in visited if by_id[n]['ifc_type']=='IfcAirTerminal']
        flows=[r.get('psets',{}).get('FI_Tekninen',{}).get('Virtaama') for r in terminals]
        groups.append({'node_count':len(visited),'terminal_count':len(terminals),
            'terminal_raw_flow_sum':sum(float(q) for q in flows if q is not None),
            'terminal_flow_missing_count':sum(q is None for q in flows),
            'node_ids':sorted(visited)})
    coverage=[]
    for kind in sorted({r['ifc_type'] for r in records}):
        selected=[r for r in records if r['ifc_type']==kind]
        coverage.append({'ifc_type':kind,'total':len(selected),
            'with_geometric_features':sum(bool(r.get('features')) for r in selected),
            'no_supported_features':sum(r['status']=='NO_SUPPORTED_CIRCULAR_FEATURES' for r in selected),
            'extraction_failed':sum(r['status']=='EXTRACTION_FAILED' for r in selected)})
    return {'model_id':model,'member_count':len(records),'coverage_by_class':coverage,
        'candidate_port_count':len(ports),'numerical_match_count':len(pairs),
        'unmatched_port_count':sum(degree[p['port_id']]==0 for p in ports),
        'unique_match_port_count':sum(degree[p['port_id']]==1 for p in ports),
        'ambiguous_port_count':sum(degree[p['port_id']]>1 for p in ports),
        'candidate_graph_groups':sorted(groups,key=lambda g:(-g['node_count'],g['node_ids'][0])),
        'flow_direction':'UNRESOLVED','physical_network_certification':'NOT_PASSED'}


def main():
    project=Path(__file__).resolve().parents[1]
    source_root=project.parent/'extracted/HVAC/IFC'
    output=project/'milestones/reproducibility/network-interfaces'
    output.mkdir(parents=True,exist_ok=True)
    helper_paths=[Path(__file__),Path(__file__).with_name('verify_paired_boundary.py'),
                  Path(__file__).with_name('recover_fitting_interfaces.py')]
    code_hashes={p.name:sha(p) for p in helper_paths}
    reports=[]
    source_hashes={}
    for material in ['Concrete','Timber']:
        model=f'HVAC_NordicLCA_Office_{material}_BuildingPermit'
        path=source_root/(model+'.ifc')
        source_hashes[model]=sha(path)
        signature=hashlib.sha256(json.dumps({'source':source_hashes[model],'code':code_hashes,'system':SYSTEM},sort_keys=True).encode()).hexdigest()
        print('Opening original IFC:',model,flush=True)
        source=ifcopenshell.open(str(path))
        groups=[g for g in source.by_type('IfcDistributionSystem') if g.Name==SYSTEM]
        if len(groups)!=1:
            raise ValueError('Exact system assignment is missing or ambiguous')
        members={e.id():e for relation in groups[0].IsGroupedBy for e in relation.RelatedObjects}
        scale=ifcopenshell.util.unit.calculate_unit_scale(source)
        settings=ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS,True)
        cache=project/'.dsh-state/network-interface-cache'/model
        cache.mkdir(parents=True,exist_ok=True)
        records=[]
        for index,entity in enumerate(sorted(members.values(),key=lambda e:e.id()),1):
            cache_path=cache/(str(entity.id())+'.json')
            record=None
            if cache_path.exists():
                saved=json.loads(cache_path.read_text(encoding='utf-8'))
                mesh_path=Path(saved['mesh_path']) if saved.get('mesh_path') else None
                if saved.get('cache_signature')==signature and mesh_path and mesh_path.exists() and sha(mesh_path)==saved['mesh_sha256']:
                    record=saved
            if record is None:
                try:
                    record=extract_entity(entity,settings,scale,cache_path,signature)
                except Exception as error:
                    record={'cache_signature':signature,'ifc_id':entity.id(),'guid':getattr(entity,'GlobalId',None),
                        'ifc_type':entity.is_a(),'name':getattr(entity,'Name',None),'features':[],
                        'status':'EXTRACTION_FAILED','error':repr(error)}
                cache_path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
            records.append(record)
            if index%100==0 or index==len(members):
                print(f'{material}: {index}/{len(members)} components inspected',flush=True)
        group_id=groups[0].id()
        del source
        source_after=sha(path)
        if source_after!=source_hashes[model]:
            raise ValueError('Original IFC hash changed during extraction; invalidate current output')
        ports=[]
        for record in records:
            for index,feature in enumerate(record.get('features',[])):
                ports.append({**feature,'port_id':f"{record['ifc_id']}:{index}",'ifc_id':record['ifc_id'],
                    'guid':record['guid'],'ifc_type':record['ifc_type'],'status':'GEOMETRIC_FEATURE_NOT_NATIVE_PORT'})
        pairs=match_features(ports)
        summary=summarize(model,records,ports,pairs)
        degree=Counter(p for edge in pairs for p in [edge['port_a'],edge['port_b']])
        for port in ports:
            port['matching_candidate_count']=degree[port['port_id']]
        result={'artifact_type':'full_system_geometric_interface_audit','status':'REQUIRES_REVIEW',
            'model_id':model,'system_name':SYSTEM,'group_ifc_id':group_id,
            'sourceSha256':source_hashes[model],'sourceSha256_after':source_after,'codeHashes':code_hashes,'cache_signature':signature,
            'length_unit_scale_to_m':scale,'numerical_match_criteria':{'center_m':CENTER_TOL,'radius_m':RADIUS_TOL,'angle_deg':ANGLE_TOL_DEG},
            'criteria_scope':'Numerical near-equality only, not engineering joint approval.',
            'components':records,'candidate_ports':ports,'candidate_matches':pairs,'summary':summary}
        (output/(material.lower()+'-interfaces.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
        reports.append(summary)
        print(json.dumps({k:v for k,v in summary.items() if k!='candidate_graph_groups'},ensure_ascii=True,indent=2),flush=True)
    result={'status':'REQUIRES_REVIEW_NOT_FORMAL_EXPERIMENT','sourceHashes':source_hashes,'codeHashes':code_hashes,'models':reports,
            'limitations':['Circular geometry features can be covers or decorative rings; no source semantic assignment certification.',
                'All ambiguous matches retained; no nearest neighbor automatically chosen.',
                'Rectangular/unsupported interfaces and missing source performance remain blockers.',
                'No pressure, energy, optimization or carbon comparison computed.']}
    (output/'network-interface-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print('Complete geometric-interface audit; scientific status remains REQUIRES_REVIEW.',flush=True)


if __name__=='__main__':
    main()
