"""Editable tables and claim-level provenance from validated synthetic results only."""
import csv
import hashlib
import json
from pathlib import Path

P=Path(__file__).resolve().parent.parent
B=P/'milestones/reproducibility/synthetic-data'
R=P/'experiments/results/synthetic-route-size-results.json'


def main():
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    result=json.loads(R.read_text(encoding='utf-8'));hash_result=sha(R)
    for name in ['data-validation.json','statistical-audit.json','reproduction-check.json']:
        gate=json.loads((B/name).read_text(encoding='utf-8'))
        if gate['status']!='PASS_SYNTHETIC_ONLY' or gate['resultSha256']!=hash_result:raise ValueError('Result gate stale: '+name)
    summary=json.loads((B/'synthetic-summary.json').read_text(encoding='utf-8'))
    if summary['resultSha256']!=hash_result:raise ValueError('Summary stale')
    candidates={c['id']:c for c in result['candidates']};table=[]
    for s in summary['rows']:
        selected=candidates.get(s['selected'])
        nominal=next(r for r in result['raw_records'] if r['weight']==s['weight'] and r['velocity_limit_m_s']==s['velocity_limit_m_s'] and r['policy']==s['policy'] and r['scenario']=='S01')
        table.append({**s,'route_length_m':selected['length_m'] if selected else None,'diameter_m':selected['diameter_m'] if selected else None,
            'nominal_cost_proxy':nominal['cost_proxy'],'score_unit':'dimensionless_synthetic_score'})
    table_dir=P/'milestones/reproducibility/tables';table_dir.mkdir(exist_ok=True)
    with (table_dir/'synthetic-method-comparison.tsv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(table[0]),delimiter='\t');writer.writeheader();writer.writerows(table)
    main_cell=[x for x in table if x['weight']==1 and x['velocity_limit_m_s']==5]
    def display(x):return 'NA' if x is None else f'{x:.4f}' if isinstance(x,float) else str(x)
    lines=['# Synthetic method comparison — predeclared main cell',
        '', 'Question: under the fixed synthetic main setting, which policies remain feasible on all held-out stress scenarios?',
        '', 'Data origin: SYNTHETIC_METHOD_BENCHMARK_01. This table is method validation, not field HVAC evidence.',
        '', '| Policy | Selected | Length (m) | Diameter (m) | Nominal proxy score (dimensionless) | Held-out failures /12 | Maximum regret over all held-out scenarios (dimensionless) |',
        '|---|---|---:|---:|---:|---:|---:|']
    for x in main_cell:
        lines.append('| '+ ' | '.join([x['policy'],str(x['selected']),display(x['route_length_m']),display(x['diameter_m']),display(x['nominal_cost_proxy']),str(x['failure_count']),display(x['maximum_regret_all_held_out'])])+' |')
    lines.extend(['','NA means all-scenario regret is undefined because at least one scenario is infeasible; it is not zero regret. Failure counts include all12 predeclared held-out scenarios. No significance tests or confidence intervals apply to this deterministic designed stress set. Length and diameter reflect synthetic alternatives around a source-geometry anchor, not observed installed replacements. All96 policy/cell rows, including no-feasible-selection outcomes, are retained in the TSV. No performance ranking is pooled across different objective weights or velocity rules.',
        '', 'Results SHA256: '+hash_result,'.'])
    (table_dir/'synthetic-method-comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    register=json.loads((B/'synthetic-data-register.json').read_text(encoding='utf-8'))
    reglines=['# Synthetic data register — editable view','', 'Generated from the canonical JSON; never edit this view to change inputs.','',
        '| Field | Value | Unit | Source grade | Basis / assumptions | Plausibility range (declared assumptions only) | Use | Sensitivity | Real replacement | Status |',
        '|---|---|---|---|---|---|---|---|---|---|']
    for x in register['fields']:
        support=x['sensitivity'] if isinstance(x['sensitivity'],list) else x['value']
        if isinstance(support,list) and all(type(v) in (int,float) for v in support):
            plausibility=f'Declared support {min(support)} to {max(support)} {x["unit"]}; assumption, not externally validated range'
        elif type(support) in (int,float):
            plausibility=f'Fixed {support} {x["unit"]}; outside-value plausibility not investigated'
        elif support is None:plausibility='Not modelled; no physical range or performance inferred'
        else:plausibility='Source geometry scale only; service and installation qualification absent'
        values=[x['field'],json.dumps(x['value'],ensure_ascii=False),x['unit'],x['source_grade'],x['generation_basis']+'; '+x['assumptions'],plausibility,x['use'],str(x['sensitivity']),x['replacement_source'],x['status']]
        reglines.append('| '+' | '.join(v.replace('|','/') for v in values)+' |')
    (B/'synthetic-data-register.md').write_text('\n'.join(reglines)+'\n',encoding='utf-8')
    prov=P/'milestones/reproducibility/result-provenance.tsv'
    # This is the numeric-claim ledger distinct from result-level milestones/result-provenance.tsv.
    if prov.exists():
        archive=P/'.dsh-state/result-validation-history';archive.mkdir(parents=True,exist_ok=True)
        (archive/('numeric-provenance-'+sha(prov)+'.tsv')).write_bytes(prov.read_bytes())
    with prov.open('w',encoding='utf-8',newline='') as f:
        fields=['claim_id','manuscript_value','source_file','source_sha256','row_filter','columns','analysis_script','output_field','status']
        writer=csv.DictWriter(f,fieldnames=fields,delimiter='\t');writer.writeheader()
        for i,x in enumerate(main_cell):
            for field in ['failure_count','feasibility_fraction','maximum_regret_all_held_out','nominal_cost_proxy','route_length_m','diameter_m']:
                writer.writerow({'claim_id':f'SYN{i+1}:{field}','manuscript_value':display(x[field]),'source_file':str(R.relative_to(P)),
                    'source_sha256':hash_result,'row_filter':f"data_origin=SYNTHETIC_METHOD_BENCHMARK_01;weight=1;velocity_limit_m_s=5;policy={x['policy']}",
                    'columns':'raw_records.cost_proxy/feasible/oracle_proxy; candidates.length_m/diameter_m',
                    'analysis_script':'code/summarize_synthetic_benchmark.py','output_field':field,'status':'VERIFIED'})
    shared_prov=P/'milestones/result-provenance.tsv'
    if shared_prov.exists() and shared_prov.read_bytes()!=prov.read_bytes():
        archive=P/'.dsh-state/result-validation-history';archive.mkdir(parents=True,exist_ok=True)
        (archive/('workflow-provenance-'+sha(shared_prov)+'.tsv')).write_bytes(shared_prov.read_bytes())
    shared_prov.write_bytes(prov.read_bytes())
    report={'artifact_type':'synthetic_table_and_register_views','status':'PASS_VALIDATED_SYNTHETIC_DISPLAY_ONLY','codeSha256':sha(Path(__file__)),
        'resultSha256':hash_result,'source_files':[{'path':str(x),'sha256':sha(x)} for x in [R,B/'synthetic-summary.json',B/'synthetic-data-register.json']],
        'outputs':[{'path':str(x),'sha256':sha(x)} for x in [table_dir/'synthetic-method-comparison.tsv',table_dir/'synthetic-method-comparison.md',B/'synthetic-data-register.md',prov,shared_prov]],
        'table_rows':len(table),'main_cell_rows':len(main_cell),'data_origin':result['data_origin'],'formal_field_evidence':False}
    (B/'synthetic-table-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'tables':len(table),'main_cell':main_cell},indent=2))


if __name__=='__main__':main()
