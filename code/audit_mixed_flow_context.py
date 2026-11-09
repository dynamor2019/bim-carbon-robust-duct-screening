"""Trace local mixed-section geometric peers; do not assign directions or fill fitting flows."""
import json
from pathlib import Path
from recover_fitting_interfaces import sha


def main():
    project=Path(__file__).resolve().parents[1]
    folder=project/'milestones/reproducibility/network-interfaces'
    mixed_path=folder/'mixed-section-review.json'
    mixed=json.loads(mixed_path.read_text(encoding='utf-8'))
    hashes={mixed_path.name:sha(mixed_path)}
    models=[]
    for material,review in zip(['concrete','timber'],mixed['models']):
        path=folder/(material+'-interfaces.json')
        hashes[path.name]=sha(path)
        if mixed['inputHashes'][path.name]!=hashes[path.name]:
            raise ValueError('Stale mixed-section input')
        data=json.loads(path.read_text(encoding='utf-8'))
        records={record['ifc_id']:record for record in data['components']}
        ports={port['port_id']:port for port in data['candidate_ports']}
        transitions=[]
        for component in review['components']:
            if not (component['qualified_rectangular_boundaries'] and component['circular_candidate_ports']):
                continue
            circle_ids={port['port_id'] for port in component['circular_candidate_ports']}
            peers=[]
            for match in data['candidate_matches']:
                a,b=match['port_a'],match['port_b']
                if (a in circle_ids)==(b in circle_ids):
                    continue
                peer=ports[b if a in circle_ids else a]
                source=records[peer['ifc_id']]
                peers.append({'transition_circle_port':a if a in circle_ids else b,'peer_port':peer['port_id'],
                    'peer_ifc_id':source['ifc_id'],'peer_name':source['name'],
                    'peer_raw_flow':source['psets'].get('FI_Tekninen',{}).get('Virtaama'),
                    'numerical_match':match})
            transitions.append({'ifc_id':component['ifc_id'],'name':component['name'],
                'transition_raw_flow':component['source_raw_flow'],
                'rectangular_matches':[m for m in review['matches'] if component['ifc_id'] in (m['component_a'],m['component_b'])],
                'circular_peers':peers})
        source_pairs=[]
        for match in review['matches']:
            a,b=records[match['component_a']],records[match['component_b']]
            qa=a['psets'].get('FI_Tekninen',{}).get('Virtaama')
            qb=b['psets'].get('FI_Tekninen',{}).get('Virtaama')
            source_pairs.append({'component_a':a['ifc_id'],'name_a':a['name'],'source_flow_a':qa,
                'component_b':b['ifc_id'],'name_b':b['name'],'source_flow_b':qb,
                'both_source_flows_present':qa is not None and qb is not None,
                'raw_difference':qa-qb if qa is not None and qb is not None else None,
                'involves_named_cap':match['involves_named_cap']})
        models.append({'model_id':data['model_id'],'transitions':transitions,'rectangular_source_pairs':source_pairs})
    result={'artifact_type':'local_mixed_section_source_flow_context','status':'LOCAL_GEOMETRIC_CONTEXT_ONLY',
        'inputHashes':hashes,'codeSha256':sha(Path(__file__)),'models':models,
        'limitations':['Null fitting flow is retained, not filled from adjacent pipe values.',
            'Zero-flow branches and named caps are retained; no positive through-flow forced.',
            'No directed conservation claim or internal passage certified from geometric matches.',
            'Local context does not certify a complete 302 fan-to-terminal service network.']}
    (folder/'mixed-flow-context.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps(models,ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
