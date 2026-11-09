"""User-authorized synthetic finite route/size experiment; no field energy/carbon model."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
from finite_candidate_decisions import Evaluation, NoFeasibleDesign, select

PROJECT=Path(__file__).resolve().parent.parent
REGISTER=PROJECT/'milestones/reproducibility/synthetic-data/synthetic-data-register.json'
SOURCE=PROJECT/'milestones/reproducibility/local-spatial-domain-freeze.json'
PROTOCOL=PROJECT/'milestones/synthetic-benchmark-protocol.md'
OUTPUT=PROJECT/'experiments/results/synthetic-route-size-results.json'
POLICIES=['source_shaped_reference','shortest_then_size','fixed_section_route','deterministic_joint',
    'robust_joint_minimax','robust_joint_regret','ablation_fixed_shortest','ablation_no_proxy']


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()


def inputs():
    r=json.loads(REGISTER.read_text(encoding='utf-8'));source=json.loads(SOURCE.read_text(encoding='utf-8'))
    fields={f['field']:f['value'] for f in r['fields']}
    required=['route_offsets_m','route_clear_widths_m','diameters_m','design_flow_m3_s','held_out_flow_m3_s',
        'design_clearance_m','held_out_clearance_m','velocity_limit_m_s','proxy_weight','reference_diameter_m',
        'reference_flow_m3_s','bend_penalty','arithmetic_tolerance','candidate_budget']
    if any(k not in fields for k in required):raise ValueError('Missing registered synthetic field')
    for k in required:
        values=fields[k] if isinstance(fields[k],list) else [fields[k]]
        if not values or any(type(v) not in (float,int) or not math.isfinite(v) or v<0 for v in values):
            raise ValueError('Invalid numeric register field: '+k)
    if fields['reference_flow_m3_s']<=0 or fields['reference_diameter_m']<=0 or min(fields['diameters_m'])<=0:
        raise ValueError('Positive normalization/diameters required')
    if len(fields['route_offsets_m'])!=len(fields['route_clear_widths_m']) or len(fields['design_flow_m3_s'])!=len(fields['design_clearance_m']):
        raise ValueError('Paired arrays differ')
    if not source['main_analysis']['candidates']==[]:raise ValueError('Do not silently promote real main domain')
    if r['scope']!='SOURCE_SCALE_ANCHORED_SYNTHETIC_FINITE_ROUTE_SIZE_METHOD_VALIDATION':raise ValueError('Wrong source scope')
    a,b=source['selected_source']['end_a_m'],source['selected_source']['end_b_m']
    length=math.dist(a,b)
    if length<=0 or abs(a[2]-b[2])>1e-10:raise ValueError('This synthetic generator requires a nonzero horizontal source axis')
    if abs(length-source['selected_source']['axis_length_m'])>1e-10:raise ValueError('Anchor mismatch')
    return r,fields,source,length


def generate(fields,source,length):
    a=source['selected_source']['end_a_m'];b=source['selected_source']['end_b_m']
    tangent=[(b[i]-a[i])/length for i in range(3)];normal=[-tangent[1],tangent[0],0]
    candidates=[]
    for route,(offset,width) in enumerate(zip(fields['route_offsets_m'],fields['route_clear_widths_m'])):
        coords=[a,b] if offset==0 else [a,[a[i]+offset*normal[i] for i in range(3)],
            [b[i]+offset*normal[i] for i in range(3)],b]
        route_length=sum(math.dist(x,y) for x,y in zip(coords,coords[1:]))
        for d in fields['diameters_m']:
            candidates.append({'id':f'R{route}_D{d:.3f}','route':route,'diameter_m':d,'length_m':route_length,
                'width_m':width,'turns':0 if offset==0 else 2,'points_m':coords,
                'data_origin':'SYNTHETIC_PASSAGE_AND_SIZE_SOURCE_GEOMETRY_ANCHOR'})
    if len(candidates)!=fields['candidate_budget'] or len({c['id'] for c in candidates})!=len(candidates):
        raise ValueError('Incomplete/duplicate candidate library')
    design=[{'id':f'S{i:02d}','split':'design','flow_m3_s':q,'clearance_m':c}
        for i,(q,c) in enumerate(zip(fields['design_flow_m3_s'],fields['design_clearance_m']))]
    holdout=[{'id':f'H{i:02d}','split':'held_out','flow_m3_s':q,'clearance_m':c}
        for i,(q,c) in enumerate((q,c) for q in fields['held_out_flow_m3_s'] for c in fields['held_out_clearance_m'])]
    return candidates,design,holdout


def evaluate(candidate,scenario,f,length,weight,velocity_limit):
    d=candidate['diameter_m'];q=scenario['flow_m3_s'];margin=scenario['clearance_m']
    velocity=q/(math.pi*d*d/4)
    feasible=d+2*margin<=candidate['width_m']+f['arithmetic_tolerance'] and velocity<=velocity_limit+f['arithmetic_tolerance']
    if not feasible:return Evaluation(False,None)
    ratio=d/f['reference_diameter_m']
    cost=candidate['length_m']/length*(ratio**2+weight*(q/f['reference_flow_m3_s'])**2/ratio**5)+f['bend_penalty']*candidate['turns']
    return Evaluation(True,cost)


def choose(policy,candidates,design,f,length,weight,velocity):
    scenarios=[s['id'] for s in design];nominal=scenarios[1]
    evaluations={c['id']:{s['id']:evaluate(c,s,f,length,weight,velocity) for s in design} for c in candidates}
    feasible_nominal=[c for c in candidates if evaluations[c['id']][nominal].feasible]
    if policy=='source_shaped_reference':return next(c['id'] for c in candidates if c['route']==0 and c['diameter_m']==f['reference_diameter_m'])
    if not feasible_nominal:raise NoFeasibleDesign('No nominally feasible candidate')
    shortest=min(c['length_m'] for c in feasible_nominal)
    pool=[c for c in candidates if c['length_m']==shortest] if policy in ('shortest_then_size','ablation_fixed_shortest') else candidates
    if policy=='fixed_section_route':pool=[c for c in candidates if c['diameter_m']==f['reference_diameter_m']]
    subset={c['id']:evaluations[c['id']] for c in pool}
    if policy=='ablation_no_proxy':subset={c['id']:{s['id']:evaluate(c,s,f,length,0,velocity) for s in design} for c in pool}
    if policy=='robust_joint_regret':
        # Scenario oracle remains common full18 candidates, not robust subset.
        return select(evaluations,scenarios,'minimax_regret')['selected']
    mode='minimax' if policy in ('robust_joint_minimax','ablation_fixed_shortest','ablation_no_proxy') else 'deterministic'
    return select(subset,scenarios,mode,nominal)['selected']


def sanity_report():
    r,f,s,length=inputs();candidates,design,holdout=generate(f,s,length)
    all_s=design+holdout
    checks=[{'name':'synthetic_origin_registered','status':'PASS','evidence':r['scope']},
        {'name':'raw_main_not_promoted','status':'PASS','evidence':'source main candidates remain empty'},
        {'name':'finite_candidate_count','status':'PASS','evidence':str(len(candidates))},
        {'name':'disjoint_scenario_ids','status':'PASS' if not set(x['id'] for x in design)&set(x['id'] for x in holdout) else 'FAIL','evidence':'3design/12heldout'},
        {'name':'envelope_diameter_and_flow_positive','status':'PASS' if all(x['flow_m3_s']>0 for x in all_s) and all(c['width_m']>0 for c in candidates) else 'FAIL','evidence':'local branch values, not3.6system demand'},
        {'name':'every_scenario_has_eligible_candidate_across_declared_velocity_sensitivity','status':'PASS' if all(any(evaluate(c,x,f,length,1,v).feasible for c in candidates) for x in all_s for v in [3,5,7]) else 'FAIL','evidence':'full enumeration3/5/7m/s; retain individual candidate failures'},
        {'name':'no_fan_or_carbon_values','status':'PASS' if f['fan_pressure_efficiency_energy_carbon'] is None else 'FAIL','evidence':'dimensionless proxy only'}]
    hashes={str(p.relative_to(PROJECT)):sha(p) for p in [REGISTER,SOURCE,PROTOCOL,Path(__file__)]}
    return {'artifact_type':'synthetic_input_sanity','status':'PASS_SYNTHETIC_INPUT_SANITY_ONLY' if all(x['status']=='PASS' for x in checks) else 'FAIL',
        'data_origin':r['dataset_id'],'codeSha256':sha(Path(__file__)),'sourceHashes':hashes,
        'source_files':[{'path':str(PROJECT/k),'sha256':v} for k,v in hashes.items() if PROJECT/k!=Path(__file__)],
        'candidateSetSha256':digest(candidates),'checks':checks,'field_registry_hash':sha(REGISTER),
        'nominal_velocity_range_m_s':[f['reference_flow_m3_s']/(math.pi*max(f['diameters_m'])**2/4), f['reference_flow_m3_s']/(math.pi*min(f['diameters_m'])**2/4)],
        'not_field_certification':True}


def run():
    sanity=sanity_report()
    if sanity['status']!='PASS_SYNTHETIC_INPUT_SANITY_ONLY':raise ValueError('Input sanity failed')
    # Match pre-run freeze, do not silently change a parameter after inspection.
    stored=json.loads((PROJECT/'milestones/reproducibility/synthetic-data/synthetic-input-sanity.json').read_text(encoding='utf-8'))
    if stored['sourceHashes']!=sanity['sourceHashes']:raise ValueError('Synthetic freeze stale; rerun input checks before experiment')
    r,f,source,length=inputs();candidates,design,holdout=generate(f,source,length)
    lookup={c['id']:c for c in candidates};rows=[];selections=[]
    for weight in [0,0.25,1,4]:
        for velocity in [3,5,7]:
            for policy in POLICIES:
                try:chosen=choose(policy,candidates,design,f,length,weight,velocity);failure=None
                except NoFeasibleDesign as error:chosen=None;failure=str(error)
                selections.append({'weight':weight,'velocity_limit_m_s':velocity,'policy':policy,'selected':chosen,'selection_failure':failure})
                for scenario in design+holdout:
                    valid=[evaluate(c,scenario,f,length,weight,velocity).cost for c in candidates if evaluate(c,scenario,f,length,weight,velocity).feasible]
                    oracle=min(valid) if valid else None
                    value=evaluate(lookup[chosen],scenario,f,length,weight,velocity) if chosen else Evaluation(False,None)
                    rows.append({'data_origin':r['dataset_id'],'weight':weight,'velocity_limit_m_s':velocity,'policy':policy,'selected':chosen,
                        'scenario':scenario['id'],'split':scenario['split'],'flow_m3_s':scenario['flow_m3_s'],'clearance_m':scenario['clearance_m'],
                        'feasible':value.feasible,'cost_proxy':value.cost,'cost_unit':'dimensionless_synthetic_score',
                        'oracle_proxy':oracle,'regret_proxy':value.cost-oracle if value.feasible else None,
                        'regret_scope':'SUPPLIED18_CANDIDATES_ONLY'})
    cleaned=[]
    for row in rows:
        record={k:(v if v is not None else ('NO_FEASIBLE_SELECTION' if k=='selected' else 'UNDEFINED_INFEASIBLE')) for k,v in row.items()}
        record['instance_id']=f"w{row['weight']}:v{row['velocity_limit_m_s']}:{row['policy']}:{row['scenario']}"
        record['loss_status']='DEFINED_SYNTHETIC_SCORE' if row['feasible'] else 'UNDEFINED_INFEASIBLE'
        cleaned.append(record)
    result={'artifact_type':'synthetic_finite_route_size_experiment','data_origin':r['dataset_id'],
        'scope':r['scope'],'field_evidence':False,'energy_and_carbon_reportable':False,
        'codeSha256':sha(Path(__file__)),'sourceHashes':sanity['sourceHashes'],
        'helperHashes':{'finite_candidate_decisions.py':sha(PROJECT/'code/finite_candidate_decisions.py')},
        'candidateSetSha256':digest(candidates),'candidates':candidates,'design_scenarios':design,'held_out_scenarios':holdout,
        'selections':selections,'records':cleaned,'raw_records':rows,
        'cleaning':{'purpose':'explicit non-applicable status for generic table validation','raw_null_scores_preserved':True,
            'no_numeric_backfill':True,'undefined_score_marker':'UNDEFINED_INFEASIBLE','missing_selection_marker':'NO_FEASIBLE_SELECTION'},'environment':{'python':platform.python_version(),'platform':platform.platform()},
        'command':'python -X utf8 code/run_synthetic_route_size.py','seed':None,'randomness':'none',
        'global_route_optimality_certified':False}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(OUTPUT),'rows':len(rows),'data_origin':r['dataset_id'],'resultSha256':sha(OUTPUT)}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--validate-only',action='store_true');parser.add_argument('--results-file',default=str(OUTPUT));args=parser.parse_args()
    chosen_output=Path(args.results_file).resolve()
    if chosen_output!=OUTPUT.resolve():raise ValueError('Output must match the registered synthetic result path')
    if args.validate_only:
        report=sanity_report();out=PROJECT/'milestones/reproducibility/synthetic-data/synthetic-input-sanity.json'
        out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'status':report['status'],'checks':report['checks']},indent=2))
        raise SystemExit(0 if report['status']=='PASS_SYNTHETIC_INPUT_SANITY_ONLY' else 2)
    run()
