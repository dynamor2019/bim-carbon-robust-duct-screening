"""Derive manuscript/display evidence from the already validated synthetic run; no new experiment."""
import csv
import hashlib
import io
import json
from pathlib import Path
from validate_synthetic_benchmark import raw_reconstruct

P=Path(__file__).resolve().parent.parent
R=P/'experiments/results/synthetic-route-size-results.json'
EXPECTED='81db9b24b6642feba61fe44ce75e3182b56dbbe8f1597153bcb1851bfe57e781'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    if sha(R)!=EXPECTED:raise ValueError('Current experiment hash changed; revalidate before prose')
    data=json.loads(R.read_text(encoding='utf-8'));rows=data['raw_records'];summary=json.loads((P/'milestones/reproducibility/synthetic-data/synthetic-summary.json').read_text(encoding='utf-8'))
    for name in ['data-validation.json','statistical-audit.json','reproduction-check.json']:
        gate=json.loads((P/'milestones/reproducibility/synthetic-data'/name).read_text(encoding='utf-8'))
        if gate['status']!='PASS_SYNTHETIC_ONLY' or gate['resultSha256']!=EXPECTED:raise ValueError('Stale gate '+name)
    f,library,design,heldout,value=raw_reconstruct();lookup={c[0]:c for c in library};scenarios={s[0]:s for s in design+heldout}
    # Independently reconstruct every raw score before deriving display values.
    for row in rows:
        expected=value(lookup[row['selected']],scenarios[row['scenario']],row['weight'],row['velocity_limit_m_s']) if row['selected'] else None
        if (expected is None)!=(row['cost_proxy'] is None) or (expected is not None and abs(expected-row['cost_proxy'])>1e-10):raise ValueError('Independent score mismatch')
    main_rows=[]
    for s in summary['rows']:
        if s['weight']!=1 or s['velocity_limit_m_s']!=5:continue
        chosen=next(c for c in data['candidates'] if c['id']==s['selected'])
        subset=[r for r in rows if r['weight']==1 and r['velocity_limit_m_s']==5 and r['policy']==s['policy']]
        nominal=next(r for r in subset if r['scenario']=='S01')
        main_rows.append({**s,'length_m':chosen['length_m'],'diameter_m':chosen['diameter_m'],'nominal_score':nominal['cost_proxy'],
            'maximum_design_score':max(r['cost_proxy'] for r in subset if r['split']=='design') if all(r['feasible'] for r in subset if r['split']=='design') else None,
            'held_out_failed_ids':[r['scenario'] for r in subset if r['split']=='held_out' and not r['feasible']]})
    policy_order=[s['policy'] for s in main_rows]
    sensitivity=[]
    for pol in policy_order:
        values=[s for s in summary['rows'] if s['policy']==pol]
        sensitivity.append({'policy':pol,'minimum_failure_count':min(s['failure_count'] for s in values),'maximum_failure_count':max(s['failure_count'] for s in values),
            'no_design_selection_count':sum(s['selected'] is None for s in values),'cell_count':len(values)})
    evidence={'artifact_type':'validated_synthetic_manuscript_display_evidence','data_origin':data['data_origin'],'field_evidence':False,'energy_and_carbon_reportable':False,
        'resultSha256':EXPECTED,'codeSha256':sha(Path(__file__)),'source_files':[{'path':str(R),'sha256':EXPECTED}],
        'parameters':f,'candidate_count':len(library),'design_count':len(design),'held_out_count':len(heldout),
        'cell_count':len({(r['weight'],r['velocity_limit_m_s']) for r in rows}),'policy_count':len(policy_order),'selection_count':len(data['selections']),'record_count':len(rows),
        'main':main_rows,'sensitivity':sensitivity,'all_cells':summary['rows'],'policy_order':policy_order,
        'independent_raw_score_check':'PASS','no_design_selection_count':sum(s['selected'] is None for s in data['selections'])}
    out=P/'milestones/reproducibility/results/manuscript-evidence.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(evidence,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    ledger=P/'milestones/reproducibility/result-provenance.tsv'
    old=list(csv.DictReader(ledger.open(encoding='utf-8'),delimiter='\t'))
    old=[r for r in old if not r['claim_id'].startswith('REPORT:')]
    def entry(claim,val,filter_,field):return {'claim_id':'REPORT:'+claim,'manuscript_value':str(val),'source_file':str(out.relative_to(P)),
        'source_sha256':sha(out),'row_filter':filter_+';data_origin=SYNTHETIC_METHOD_BENCHMARK_01','columns':field,
        'analysis_script':'code/prepare_manuscript_evidence.py','output_field':field,'status':'VERIFIED'}
    for field in ['candidate_count','design_count','held_out_count','cell_count','policy_count','selection_count','record_count','no_design_selection_count']:
        old.append(entry(field,evidence[field],'all generated records',field))
    for s in sensitivity:
        for field in ['minimum_failure_count','maximum_failure_count','no_design_selection_count']:
            old.append(entry(s['policy']+':'+field,s[field],'sensitivity.policy='+s['policy'],'sensitivity.'+field))
    for s in main_rows:
        for field in ['length_m','diameter_m','nominal_score','maximum_design_score','maximum_regret_all_held_out']:
            old.append(entry(s['policy']+':'+field,'NA_UNDEFINED_INFEASIBLE' if s[field] is None else s[field],'main.policy='+s['policy']+';weight=1;velocity=5','main.'+field))
    fields=['claim_id','manuscript_value','source_file','source_sha256','row_filter','columns','analysis_script','output_field','status']
    buffer=io.StringIO();writer=csv.DictWriter(buffer,fieldnames=fields,delimiter='\t',lineterminator='\n');writer.writeheader();writer.writerows(old)
    archive=P/'.dsh-state/result-validation-history';archive.mkdir(parents=True,exist_ok=True)
    for target in [ledger,P/'milestones/result-provenance.tsv']:
        if target.exists():(archive/(target.parent.name+'-provenance-'+sha(target)+'.tsv')).write_bytes(target.read_bytes())
        target.write_text(buffer.getvalue(),encoding='utf-8')
    print(json.dumps({'status':'PASS_DERIVED_SYNTHETIC_EVIDENCE','resultSha256':EXPECTED,'main':main_rows,'sensitivity':sensitivity,'verified_claims':len(old)},indent=2))


if __name__=='__main__':main()
