"""Three distinct synthetic result checks, independently reconstructed from raw assumptions."""
import hashlib
import json
import math
from pathlib import Path

P=Path(__file__).resolve().parent.parent
R=P/'experiments/results/synthetic-route-size-results.json'
BASE=P/'milestones/reproducibility/synthetic-data'


def sha(f):return hashlib.sha256(Path(f).read_bytes()).hexdigest()
def write(name,d):
    (BASE/name).write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def check(name,ok,evidence):return {'name':name,'status':'PASS' if ok else 'FAIL','evidence':str(evidence)}


def raw_reconstruct():
    # Deliberately no imports from the experiment or finite decision module.
    register=json.loads((BASE/'synthetic-data-register.json').read_text(encoding='utf-8'))
    f={x['field']:x['value'] for x in register['fields']}
    source=json.loads((P/'milestones/reproducibility/local-spatial-domain-freeze.json').read_text(encoding='utf-8'))
    a=source['selected_source']['end_a_m'];b=source['selected_source']['end_b_m']
    length=math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
    library=[]
    for route,offset in enumerate(f['route_offsets_m']):
        for diameter in f['diameters_m']:
            library.append((f'R{route}_D{diameter:.3f}',route,diameter,length+2*offset,f['route_clear_widths_m'][route],0 if offset==0 else 2))
    designs=[(f'S{i:02d}',q,c) for i,(q,c) in enumerate(zip(f['design_flow_m3_s'],f['design_clearance_m']))]
    heldout=[]
    for q in f['held_out_flow_m3_s']:
        for c in f['held_out_clearance_m']:heldout.append((f'H{len(heldout):02d}',q,c))
    def value(candidate,scenario,w,v):
        ident,route,d,l,width,turns=candidate;s,q,c=scenario
        if d+2*c-width>f['arithmetic_tolerance'] or 4*q/(math.pi*d*d)-v>f['arithmetic_tolerance']:return None
        return l/length*((d/f['reference_diameter_m'])**2+w*(q/f['reference_flow_m3_s'])**2*(f['reference_diameter_m']/d)**5)+f['bend_penalty']*turns
    return f,library,designs,heldout,value


def main():
    d=json.loads(R.read_text(encoding='utf-8'));rows=d['raw_records'];selections=d['selections']
    result_hash=sha(R)
    hashes={str(p.relative_to(P)):sha(p) for p in [BASE/'synthetic-data-register.json',P/'milestones/reproducibility/local-spatial-domain-freeze.json',P/'milestones/synthetic-benchmark-protocol.md',R,Path(__file__)]}
    def report(kind,checks):return {'artifact_type':kind,'status':'PASS_SYNTHETIC_ONLY' if all(c['status']=='PASS' for c in checks) else 'FAIL',
        'resultSha256':result_hash,'command':'python -X utf8 code/validate_synthetic_benchmark.py','sourceHashes':hashes,
        'codeSha256':sha(Path(__file__)),'source_files':[{'path':str(P/k),'sha256':v} for k,v in hashes.items()],
        'checks':checks,'data_origin':d['data_origin'],'field_evidence':False}
    keys=[(r['weight'],r['velocity_limit_m_s'],r['policy'],r['scenario']) for r in rows]
    finite=all(all(x is None or (type(x) in (int,float) and math.isfinite(x)) for x in [r['cost_proxy'],r['oracle_proxy'],r['regret_proxy']]) for r in rows)
    arithmetic=all((not r['feasible'] and r['cost_proxy'] is None and r['regret_proxy'] is None) or
        (r['feasible'] and r['cost_proxy'] is not None and r['oracle_proxy'] is not None and abs(r['cost_proxy']-r['oracle_proxy']-r['regret_proxy'])<1e-10 and r['regret_proxy']>=-1e-10) for r in rows)
    cleaned_consistent=len(d['records'])==len(rows) and all(all(clean[k]==(value if value is not None else ('NO_FEASIBLE_SELECTION' if k=='selected' else 'UNDEFINED_INFEASIBLE')) for k,value in raw.items()) for raw,clean in zip(rows,d['records']))
    structure=[check('cleaned_table_preserves_all_raw_nulls_and_scores',cleaned_consistent,'status markers only, no deletion or numeric imputation'),check('expected_complete_shape',len(rows)==1440 and len(selections)==96 and len(d['candidates'])==18,(len(rows),len(selections),len(d['candidates']))),
        check('unique_result_keys',len(keys)==len(set(keys)),'cell/policy/scenario'),check('finite_nullable_scores',finite,'infeasible scores null; no NaN'),
        check('regret_arithmetic',arithmetic,'same-scenario candidate oracle; nonnegative'),
        check('all_rows_explicit_origin',all(r['data_origin']=='SYNTHETIC_METHOD_BENCHMARK_01' and r['cost_unit']=='dimensionless_synthetic_score' for r in rows),'synthetic method score only')]
    struct=report('synthetic_structure_integrity',structure);write('data-validation.json',struct)
    if struct['status']=='FAIL':raise SystemExit('Structure gate failed; no further gates')
    scenario_ids=set(s['id'] for s in d['design_scenarios']);hold_ids=set(s['id'] for s in d['held_out_scenarios'])
    freeze_ok=all((P/k).is_file() and sha(P/k)==v for k,v in d['sourceHashes'].items())
    selections_ok=all(len({r['selected'] for r in rows if (r['weight'],r['velocity_limit_m_s'],r['policy'])==(s['weight'],s['velocity_limit_m_s'],s['policy'])})==1 for s in selections)
    robust_ok=all(not r['selected'] or r['feasible'] for r in rows if r['split']=='design' and r['policy'] in ['robust_joint_minimax','robust_joint_regret','ablation_fixed_shortest','ablation_no_proxy'])
    common=all(len({(r['weight'],r['velocity_limit_m_s'],r['scenario']) for r in rows if r['policy']==pol})==180 for pol in {r['policy'] for r in rows})
    science=[check('freeze_hashes_match',freeze_ok,'register/source/protocol/experiment code unchanged'),
        check('design_holdout_disjoint',not scenario_ids&hold_ids and len(scenario_ids)==3 and len(hold_ids)==12,'fixed3/12 IDs'),
        check('same_domain_and_scenario_coverage',common,'18common candidates;12cells×15scenarios perpolicy'),
        check('fixed_selection_no_holdout_reselection',selections_ok,'one selected ID per policy/cell'),
        check('robust_design_feasibility_or_explicit_selection_failure',robust_ok,'robust selection must pass every design scenario'),
        check('claim_scope_synthetic_not_energy_carbon',d['field_evidence'] is False and d['energy_and_carbon_reportable'] is False and d['global_route_optimality_certified'] is False,'no physical performance, LCA or global bound'),
        check('source_main_unpromoted',json.loads((P/'milestones/reproducibility/local-spatial-domain-freeze.json').read_text(encoding='utf-8'))['main_analysis']['candidates']==[],'real domain stays empty')]
    sci=report('synthetic_scientific_scope_audit',science);write('statistical-audit.json',sci)
    if sci['status']=='FAIL':raise SystemExit('Scientific scope gate failed')
    f,library,designs,heldout,value=raw_reconstruct();lookup={x[0]:x for x in library};policies={s['policy'] for s in selections}
    mismatches=[];recomputed_selections={}
    for w in [0,.25,1,4]:
        for v in [3,5,7]:
            costs={c[0]:[value(c,s,w,v) for s in designs] for c in library}
            best=[min(x[j] for x in costs.values() if x[j] is not None) for j in range(3)]
            nominal=[c for c in library if costs[c[0]][1] is not None];shortest=min(c[3] for c in nominal)
            for pol in policies:
                if pol=='source_shaped_reference':selected=next(c[0] for c in library if c[1]==0 and c[2]==f['reference_diameter_m'])
                else:
                    pool=[c for c in library if abs(c[3]-shortest)<1e-12] if pol in ['shortest_then_size','ablation_fixed_shortest'] else list(library)
                    if pol=='fixed_section_route':pool=[c for c in pool if c[2]==f['reference_diameter_m']]
                    scores=[]
                    for c in pool:
                        values=[value(c,s,0 if pol=='ablation_no_proxy' else w,v) for s in designs]
                        if pol in ['robust_joint_minimax','robust_joint_regret','ablation_fixed_shortest','ablation_no_proxy']:
                            if any(x is None for x in values):continue
                            score=max(x-best[j] for j,x in enumerate(values)) if pol=='robust_joint_regret' else max(values)
                        else:
                            if values[1] is None:continue
                            score=values[1]
                        scores.append((score,c[0]))
                    selected=min(scores)[1] if scores else None
                recomputed_selections[(w,v,pol)]=selected
    for s in selections:
        if recomputed_selections[(s['weight'],s['velocity_limit_m_s'],s['policy'])]!=s['selected']:mismatches.append('selection:'+str(s))
    scenario_lookup={s[0]:s for s in designs+heldout}
    for row in rows:
        sc=scenario_lookup[row['scenario']];w=row['weight'];v=row['velocity_limit_m_s']
        expected=value(lookup[row['selected']],sc,w,v) if row['selected'] else None
        vals=[value(c,sc,w,v) for c in library];oracle=min(x for x in vals if x is not None)
        regret=expected-oracle if expected is not None else None
        for name,actual,exp in [('cost',row['cost_proxy'],expected),('oracle',row['oracle_proxy'],oracle),('regret',row['regret_proxy'],regret)]:
            if (actual is None)!=(exp is None) or (actual is not None and abs(actual-exp)>1e-10):mismatches.append(name+':'+str((row['weight'],row['velocity_limit_m_s'],row['policy'],row['scenario'])))
    replication=report('independent_synthetic_raw_parameter_recomputation',[
        check('independent_selection_recomputation',not any(x.startswith('selection:') for x in mismatches),'96 selections, independent code without runner/decision imports'),
        check('independent_all_scores_oracles_regrets',not mismatches,str(len(rows))+' raw-register reconstructed rows;1e-10 tolerance'),
        check('independent_original_candidate_count',len(library)==18,'3routes×6sizes')])
    replication['mismatches']=mismatches;write('reproduction-check.json',replication)
    if replication['status']=='FAIL':raise SystemExit('Independent recomputation failed')
    # Machine summary: no feasible-only maximum masquerading as all-scenario regret.
    summary=[]
    for selection in selections:
        held=[r for r in rows if r['split']=='held_out' and (r['weight'],r['velocity_limit_m_s'],r['policy'])==(selection['weight'],selection['velocity_limit_m_s'],selection['policy'])]
        fails=sum(not r['feasible'] for r in held)
        summary.append({**selection,'data_origin':d['data_origin'],'held_out_count':len(held),'failure_count':fails,
            'feasibility_fraction':(len(held)-fails)/len(held),
            'maximum_regret_all_held_out':max(r['regret_proxy'] for r in held) if fails==0 else None})
    write('synthetic-summary.json',{'artifact_type':'synthetic_method_summary','codeSha256':sha(Path(__file__)),
        'resultSha256':result_hash,'data_origin':d['data_origin'],'rows':summary,'source_files':[{'path':str(R),'sha256':result_hash}]})
    provenance=BASE/'result-hash-provenance.tsv'
    expected_provenance='result_path\tresult_sha256\tstatus\tevidence_scope\n'+str(R.relative_to(P))+'\t'+result_hash+'\tVERIFIED\tSYNTHETIC_METHOD_ONLY_NOT_FIELD_VALIDATION\n'
    if provenance.exists() and provenance.read_text(encoding='utf-8')!=expected_provenance:
        archive=P/'.dsh-state/result-validation-history';archive.mkdir(parents=True,exist_ok=True)
        (archive/('result-provenance-'+sha(provenance)+'.tsv')).write_bytes(provenance.read_bytes())
        provenance.write_text(expected_provenance,encoding='utf-8')
    elif not provenance.exists():provenance.write_text(expected_provenance,encoding='utf-8')
    for name,gate in [('statistical-audit.json',sci),('reproduction-check.json',replication)]:
        shared={**gate,'status':'PASS','validation_scope':'SYNTHETIC_METHOD_ONLY_NOT_FIELD_DATA','specialized_status':gate['status']}
        (P/'milestones/reproducibility'/name).write_text(json.dumps(shared,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'structure':struct['status'],'scientific_scope':sci['status'],'independent_recomputation':replication['status'],
        'resultSha256':result_hash,'rows':len(rows),'main_cell':[s for s in summary if s['weight']==1 and s['velocity_limit_m_s']==5]},indent=2))


if __name__=='__main__':main()
