"""Trace the candidate graph path between paired boundary objects; no topology certification."""
import csv
import hashlib
import json
from collections import deque
from pathlib import Path


def shortest_path(adjacency,start,end):
    previous={start:None}
    queue=deque([start])
    while queue:
        node=queue.popleft()
        if node==end:
            path=[]
            while node is not None:
                path.append(node)
                node=previous[node]
            return path[::-1]
        for other in sorted(adjacency.get(node,())):
            if other not in previous:
                previous[other]=node
                queue.append(other)
    return None


def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    project=Path(__file__).resolve().parents[1]
    root=project.parent/'research_data'
    pilot_path=root/'pilot_components_enriched.csv'
    contacts_path=root/'pilot_inferred_contacts.csv'
    pilot,contacts=rows(pilot_path),rows(contacts_path)
    queries=[('HVAC_NordicLCA_Office_Concrete_BuildingPermit','2667480','2667559'),
             ('HVAC_NordicLCA_Office_Timber_BuildingPermit','3137757','3137836')]
    records=[]
    for model,start,end in queries:
        index={r['ifc_id']:r for r in pilot if r['model_id']==model}
        edge_rows={}
        adjacency={}
        for r in contacts:
            if r['model_id']==model and float(r['tolerance_m'])==.005:
                a,b=r['component_a'],r['component_b']
                adjacency.setdefault(a,set()).add(b)
                adjacency.setdefault(b,set()).add(a)
                edge_rows[tuple(sorted((a,b)))]=r
        path=shortest_path(adjacency,start,end)
        path_records=[]
        if path:
            for i,node in enumerate(path):
                r=index[node]
                value={k:r[k] for k in ['ifc_id','ifc_guid','ifc_type','name','floor','flow_rate_raw','diameter_m','width_m','height_m']}
                value['bbox_min_m']=[float(r[f'bbox_min_{a}_m']) for a in 'xyz']
                value['bbox_max_m']=[float(r[f'bbox_max_{a}_m']) for a in 'xyz']
                if i:
                    value['incoming_candidate_edge']=edge_rows[tuple(sorted((node,path[i-1])))]
                value['same_guid_other_model']=[{'model_id':p['model_id'],'ifc_id':p['ifc_id'], 'floor':p['floor']}
                                                for p in pilot if p['model_id']!=model and p['ifc_guid']==r['ifc_guid']]
                path_records.append(value)
        records.append({'model_id':model,'start':start,'end':end,'candidate_path_found':path is not None,
                        'edge_count':len(path)-1 if path else None,'candidate_path':path_records,
                        'evidence_limit':'Shortest path in bbox candidate graph only; flow and port connectivity not validated.'})
    result={'status':'REQUIRES_REVIEW','artifact_type':'candidate_path_review',
            'sourceHashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [pilot_path,contacts_path]},
            'codeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'queries':records}
    out=project/'milestones/reproducibility/boundary-evidence/candidate-boundary-path.json'
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps(records,ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
