"""Recompute terminal summaries and paired identities from preserved source rows."""
import json
import math
from collections import Counter
from pathlib import Path
from recover_fitting_interfaces import sha


def main():
    folder=Path(__file__).resolve().parents[1]/'milestones/reproducibility/network-interfaces'
    path=folder/'terminal-service-review.json'
    data=json.loads(path.read_text(encoding='utf-8'))
    errors=[]
    summaries=[]
    for model in data['models']:
        rows=model['rows']
        if len({r['guid'] for r in rows})!=len(rows):
            errors.append(model['model_id']+': duplicate terminal GUID')
        for recorded in model['product_summary']:
            selected=[r for r in rows if r['product_family']==recorded['label']]
            if len(selected)!=recorded['count'] or not all(r['flow_m3_s'] is not None for r in selected):
                errors.append(model['model_id']+': summary count or missing flow')
            elif not math.isclose(math.fsum(r['flow_m3_s'] for r in selected),recorded['flow_sum_m3_s'],rel_tol=1e-12,abs_tol=1e-12):
                errors.append(model['model_id']+': summary sum mismatch')
        others=[r for r in rows if r['product_family']=='OTHER_SOURCE_PRODUCT']
        summaries.append({'model_id':model['model_id'],'source_terminal_sum_m3_s':math.fsum(r['flow_m3_s'] for r in rows),
            'other_names':dict(Counter(r['name'] for r in others)),
            'other_manufacturers':dict(Counter(r['source_product'].get('Tuotetyypin valmistaja') for r in others)),
            'other_descriptions':dict(Counter(r['source_product'].get('Tuotetyypin kuvaus') for r in others)),
            'other_raw_flows':dict(Counter(str(r['source_raw_flow']) for r in others)),
            'other_floor_counts':dict(Counter(r['source_floor_label'] for r in others))})
    paired=[{r['guid']:(r['name'],r['source_raw_flow'],r['source_floor_label']) for r in m['rows']} for m in data['models']]
    if paired[0]!=paired[1]:
        errors.append('Paired terminal identity/name/flow/floor mismatch')
    result={'artifact_type':'terminal_source_summary_validation','status':'FAIL' if errors else 'PASS_TERMINAL_SUMMARIES_ONLY',
        'inputHashes':{path.name:sha(path)},'codeSha256':sha(Path(__file__)),'errors':errors,'models':summaries,
        'scope':'Independent summary/identity recomputation from preserved rows only; not independent complete hydraulic reconstruction.'}
    (folder/'terminal-service-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps(result,ensure_ascii=True,indent=2))
    if errors:
        raise SystemExit(2)


if __name__=='__main__':
    main()
