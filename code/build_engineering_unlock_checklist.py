"""Generate source-bound parameter unlock checklist from current engineering gate."""
import json
from pathlib import Path
from guard_engineering_inputs import sha

PLAN={
'protocol_refreeze':('protocol amendment + analysis plan','REFREEZE_PENDING tag replaced by reviewed frozen hash; preserve original snapshot and amendment'),
'service_boundary':('RVT connector export or signed source-authored service drawing','PF01 identity, connected branches, direction, terminal scope and IFC/RVT mapping independently verified'),
'routing_domain':('registered architecture/MEP/structure models and clearance rule','coordinate registration, obstacle inclusion, space validity and installation envelope pass'),
'terminal_demands':('design schedule revision or engineer decision record','explain 3.815 versus 3.6, service scope and simultaneous demand; no rescaling'),
'fan_curve':('302PF01 manufacturer selection/commissioning curve','pressure basis, flow points, efficiency, power, density/RPM and operating range source-bound'),
'duct_catalog':('project duct schedule plus qualified product catalogue','diameter, thickness, roughness and applicability linked to each candidate'),
'fitting_loss_model':('route fitting schedule and coefficient source','every local K/alternative fitting has source and reference velocity'),
'friction_model':('frozen hydraulic method and roughness/air conditions','formula, density, roughness and validity domain independently checked'),
'installation_constraints':('design/installation drawings or engineer constraint record','clearance, bend radius, access and envelope constraints mapped to geometry'),
'velocity_limit':('applicable design standard or project criterion','maximum velocity source is applicable to this exhaust system'),
'material_mass_model':('object-linked quantity takeoff and construction specification','mass for duct/fittings/supports/insulation linked to installed alternatives'),
'epd_scope_model':('EPD and product applicability record','product identity, A1-A3/B4/B6 modules, indicator and exclusions qualified'),
'equivalent_hours_per_year':('operation schedule or labelled prospective scenario','hours separated from design flow and source/assumption status explicit'),
'analysis_horizon':('protocol amendment with horizon basis','horizon frozen before results and sensitivity rule defined'),
'replacement_rules':('component-specific service-life/replacement sources','duct/fan rules and event timing frozen; no generic lifetime transfer'),
'cost_model':('dated geography-specific cost sources','currency, year, scope, labor/installation and escalation basis bound'),
'design_scenarios':('source-qualified product/tariff/design scenario table','IDs, values, bounds and inclusion rules frozen before optimization'),
'held_out_scenarios':('pre-frozen disjoint held-out scenario table','IDs and values unavailable to selection stage and hash bound'),
'solver_budget':('protocol amendment with solver/resource specification','algorithm, time/memory budget, termination and optimality interpretation frozen')}

if __name__=='__main__':
    project=Path(__file__).resolve().parents[1]; root=project/'milestones/reproducibility'; inp=root/'engineering-inputs.json'; gate=root/'candidate-evaluation-preflight.json'
    data=json.loads(inp.read_text(encoding='utf-8')); pre=json.loads(gate.read_text(encoding='utf-8'))
    checks={c['name']:c for c in pre['result']['input_checks']}
    rows=[]
    for name,p in data['parameters'].items():
        source,condition=PLAN[name]; rows.append({'parameter':name,'gate_status':checks.get(name,{}).get('status','UNBOUND'),'blocker':p['blocker'],'required_source_type':source,'minimum_pass_condition':condition,'current_evidence_count':len(p['evidence']),'value_present':p['value'] is not None})
    binding=root/'engineering-validation-bindings.json'
    if set(data['parameters']) != set(PLAN)-{'protocol_refreeze'}:
        raise ValueError('Unlock plan must cover exact parameter schema')
    if pre.get('inputHashes',{}).get(inp.name)!=sha(inp):
        raise ValueError('Preflight binds stale input packet')
    out={'source_files':[{'path':str(p),'sha256':sha(p)} for p in (inp,gate,binding)],'protocol_requirement':{'status':checks['protocol_refreeze']['status'],'required_source_type':PLAN['protocol_refreeze'][0],'minimum_pass_condition':PLAN['protocol_refreeze'][1],'timing':'Refreeze only after source qualification and model/scenario decisions; before formal experiment.'},'artifact_type':'engineering_parameter_unlock_checklist','status':'BLOCKED_UNLOCK_PLAN_ONLY','input_sha256':sha(inp),'preflight_sha256':sha(gate),'codeSha256':sha(Path(__file__)),'parameters':rows,'ordering':['service_boundary','fan_curve','routing_domain','terminal_demands','duct_catalog','fitting_loss_model','friction_model','installation_constraints','velocity_limit','material_mass_model','epd_scope_model','equivalent_hours_per_year','analysis_horizon','replacement_rules','cost_model','design_scenarios','held_out_scenarios','solver_budget','protocol_refreeze'],'formal_experiment':False,'rule':'No parameter is populated by this checklist; every source must be independently validated and rebound after hash changes.'}
    path=root/'engineering-parameter-unlock-checklist.json'; path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':out['status'],'parameter_count':len(rows),'blocked_count':sum(r['gate_status']!='PASS' for r in rows)},ensure_ascii=True,indent=2))
