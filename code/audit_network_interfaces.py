"""Independently audit geometric inventories and export unresolved interfaces.
Uses a sorted x-window search, not the extraction script's spatial hash matcher.
This audit does not certify source topology or unlock formal optimization.
"""
import bisect
import csv
import hashlib
import json
import math
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def independent_pairs(ports,criteria):
    ordered=sorted(ports,key=lambda p:(p['center_m'][0],p['port_id']))
    xs=[p['center_m'][0] for p in ordered]
    expected=set()
    for i,port in enumerate(ordered):
        stop=bisect.bisect_right(xs,port['center_m'][0]+criteria['center_m'])
        for other in ordered[i+1:stop]:
            if other['ifc_id']==port['ifc_id']:
                continue
            if math.dist(port['center_m'],other['center_m'])>criteria['center_m']:
                continue
            dot=abs(sum(a*b for a,b in zip(port['normal_sign_arbitrary'],other['normal_sign_arbitrary'])))
            angle=math.degrees(math.acos(min(1.,max(0.,dot))))
            if angle>criteria['angle_deg']:
                continue
            if min(abs(a-b) for a in port['radii_m'] for b in other['radii_m'])>criteria['radius_m']:
                continue
            expected.add(tuple(sorted((port['port_id'],other['port_id']))))
    return expected


def write_csv(path,records,fields):
    with path.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n')
        writer.writeheader()
        writer.writerows(records)


def audit(data):
    errors=[]
    records=data['components']
    components={r['ifc_id']:r for r in records}
    ports=data['candidate_ports']
    index={p['port_id']:p for p in ports}
    if len(components)!=len(records):
        errors.append('duplicate_component_id')
    if len(index)!=len(ports):
        errors.append('duplicate_port_id')
    for p in ports:
        values=p['center_m']+p['normal_sign_arbitrary']+p['radii_m']
        if not values or not all(math.isfinite(v) for v in values) or not p['radii_m'] or min(p['radii_m'])<=0:
            errors.append('invalid_port_numeric:'+p['port_id'])
        if abs(math.sqrt(sum(v*v for v in p['normal_sign_arbitrary']))-1)>1e-8:
            errors.append('nonunit_normal:'+p['port_id'])
        r=components.get(p['ifc_id'])
        if r is None:
            errors.append('port_missing_component:'+p['port_id'])
        elif any(p['center_m'][i]<r['bbox_min_m'][i]-1e-6 or p['center_m'][i]>r['bbox_max_m'][i]+1e-6 for i in range(3)):
            errors.append('port_center_outside_mesh_bbox:'+p['port_id'])
    actual=[]
    degree=Counter()
    neighbors=defaultdict(list)
    for match in data['candidate_matches']:
        key=tuple(sorted((match['port_a'],match['port_b'])))
        actual.append(key)
        for a,b in [(match['port_a'],match['port_b']),(match['port_b'],match['port_a'])]:
            degree[a]+=1
            neighbors[a].append(b)
        if any(port_id not in index for port_id in key):
            errors.append('match_missing_port:'+str(key))
    if len(set(actual))!=len(actual):
        errors.append('duplicate_match_pair')
    expected=independent_pairs(ports,data['numerical_match_criteria']) if not errors else set()
    mismatch={'missing_in_recorded':sorted(expected-set(actual)), 'extra_in_recorded':sorted(set(actual)-expected)}
    if mismatch['missing_in_recorded'] or mismatch['extra_in_recorded']:
        errors.append('independent_match_recomputation_disagrees')
    counts={'member_count':len(records),'candidate_port_count':len(ports),'numerical_match_count':len(actual),
            'unmatched_port_count':sum(degree[p['port_id']]==0 for p in ports),
            'unique_match_port_count':sum(degree[p['port_id']]==1 for p in ports),
            'ambiguous_port_count':sum(degree[p['port_id']]>1 for p in ports)}
    for key,value in counts.items():
        if data['summary'][key]!=value:
            errors.append('summary_count_mismatch:'+key)
    parents={node:node for node in components}
    def find(node):
        while parents[node]!=node:
            parents[node]=parents[parents[node]]
            node=parents[node]
        return node
    for match in data['candidate_matches']:
        if match['ifc_a'] in parents and match['ifc_b'] in parents:
            parents[find(match['ifc_a'])]=find(match['ifc_b'])
    union_groups=defaultdict(list)
    for node in parents:
        union_groups[find(node)].append(node)
    actual_groups=sorted(sorted(g['node_ids']) for g in data['summary']['candidate_graph_groups'])
    recomputed_groups=sorted(sorted(g) for g in union_groups.values())
    if actual_groups!=recomputed_groups:
        errors.append('independent_graph_recomputation_disagrees')
    terminal_status=Counter()
    for r in records:
        if r['ifc_type']!='IfcAirTerminal':
            continue
        own=[p for p in ports if p['ifc_id']==r['ifc_id']]
        if not own:
            status='NO_CIRCULAR_FEATURES'
        elif any(degree[p['port_id']]>1 for p in own):
            status='HAS_AMBIGUOUS_NUMERICAL_MATCH'
        elif any(degree[p['port_id']]==1 for p in own):
            status='HAS_UNIQUE_NUMERICAL_MATCH_ONLY'
        else:
            status='ALL_FEATURES_UNMATCHED'
        terminal_status[status]+=1
    unresolved=[]
    for p in ports:
        if degree[p['port_id']]!=1:
            r=components[p['ifc_id']]
            unresolved.append({'model_id':data['model_id'],'port_id':p['port_id'],'ifc_id':p['ifc_id'],
                'guid':p['guid'],'ifc_type':p['ifc_type'],'name':r.get('name'),
                'center_x_m':p['center_m'][0],'center_y_m':p['center_m'][1],'center_z_m':p['center_m'][2],
                'radii_m':'|'.join(str(v) for v in p['radii_m']), 'candidate_count':degree[p['port_id']],
                'candidate_port_ids':'|'.join(sorted(neighbors[p['port_id']])),
                'status':'UNMATCHED' if degree[p['port_id']]==0 else 'AMBIGUOUS'})
    uncovered=[{'model_id':data['model_id'],'ifc_id':r['ifc_id'],'guid':r['guid'],
        'ifc_type':r['ifc_type'],'name':r.get('name'),'status':r['status'],'error':r.get('error','')}
        for r in records if not r.get('features')]
    return {'model_id':data['model_id'],'integrity_status':'PASS_CANDIDATE_INVENTORY_ONLY' if not errors else 'FAIL',
        'independent_geometric_matching':'PASS' if not errors else 'FAIL', 'errors':errors,
        'match_recomputation_differences':mismatch,'counts':counts,
        'terminal_geometric_status':dict(terminal_status),'candidate_graph_component_count':len(recomputed_groups),
        'largest_candidate_graph_components':sorted((len(g) for g in union_groups.values()),reverse=True)[:10],
        'scientific_readiness':'BLOCKED: geometry candidates are not validated service topology or hydraulic state'},unresolved,uncovered


def main():
    project=Path(__file__).resolve().parents[1]
    folder=project/'milestones/reproducibility/network-interfaces'
    results=[]
    unresolved=[]
    uncovered=[]
    input_hashes={}
    for material in ['concrete','timber']:
        path=folder/(material+'-interfaces.json')
        input_hashes[path.name]=sha(path)
        data=json.loads(path.read_text(encoding='utf-8'))
        report,missing,unsupported=audit(data)
        if data['sourceSha256']!=data['sourceSha256_after']:
            report['errors'].append('IFC_source_changed_during_extraction')
            report['integrity_status']='FAIL'
        source_path=project.parent/'extracted/HVAC/IFC'/(data['model_id']+'.ifc')
        source_current=sha(source_path)
        report['current_ifc_sha256']=source_current
        if source_current!=data['sourceSha256']:
            report['errors'].append('IFC_source_changed_since_extraction')
            report['integrity_status']='FAIL'
        for filename,digest in data['codeHashes'].items():
            if sha(project/'code'/filename)!=digest:
                report['errors'].append('extraction_code_changed:'+filename)
                report['integrity_status']='FAIL'
        results.append(report)
        unresolved.extend(missing)
        uncovered.extend(unsupported)
    result={'artifact_type':'independent_geometric_inventory_audit',
            'status':'PASS_CANDIDATE_INVENTORIES_ONLY' if all(r['integrity_status'].startswith('PASS') for r in results) else 'FAIL',
            'codeSha256':sha(Path(__file__)),'inputHashes':input_hashes,'models':results,
            'formal_experiment_gate':'NOT_PASSED; protocol, hydraulic/service audit and engineering inputs unresolved'}
    (folder/'independent-interface-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    write_csv(folder/'unresolved-ports.csv',unresolved,['model_id','port_id','ifc_id','guid','ifc_type','name','center_x_m','center_y_m','center_z_m','radii_m','candidate_count','candidate_port_ids','status'])
    write_csv(folder/'uncovered-components.csv',uncovered,['model_id','ifc_id','guid','ifc_type','name','status','error'])
    print(json.dumps(result,ensure_ascii=True,indent=2))
    if result['status']=='FAIL':
        raise SystemExit(2)


if __name__=='__main__':
    main()
