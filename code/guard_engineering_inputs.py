"""Fail-closed pre-experiment intake. Not an optimizer or post-experiment result gate."""
import argparse
import hashlib
import json
import math
from pathlib import Path

SPECS={
    'service_boundary':('schema',dict),'routing_domain':('m',dict),
    'terminal_demands':('m3/s',list),'fan_curve':('SI_curve_table',dict),
    'duct_catalog':('m',list),'fitting_loss_model':('dimensionless',dict),
    'friction_model':('SI_model',dict),'installation_constraints':('SI_constraints',dict),
    'velocity_limit':('m/s',float),'material_mass_model':('kg',dict),
    'epd_scope_model':('kgCO2e',dict),'equivalent_hours_per_year':('h/year',float),
    'analysis_horizon':('year',float),'replacement_rules':('year',dict),
    'cost_model':('EUR',dict),'design_scenarios':('scenario_set',list),
    'held_out_scenarios':('scenario_set',list),'solver_budget':('s',dict)}
GATES=('structure_integrity','scientific_applicability','independent_raw_input_recomputation')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finite_tree(value):
    if isinstance(value,float):
        return math.isfinite(value)
    if isinstance(value,dict):
        return all(finite_tree(v) for v in value.values())
    if isinstance(value,list):
        return all(finite_tree(v) for v in value)
    return True


def local_evidence(record,project):
    if not isinstance(record,dict) or not isinstance(record.get('path'),str):
        return False
    path=(project/record['path']).resolve()
    if not path.is_relative_to(project.resolve()) or not path.is_file():
        return False
    return isinstance(record.get('sha256'),str) and sha(path)==record['sha256']


def scenario_ids(rows):
    if not isinstance(rows,list) or not rows:
        return None
    ids=[]
    for row in rows:
        if not isinstance(row,dict) or not isinstance(row.get('id'),str) or not row['id'].strip():
            return None
        ids.append(row['id'])
    return ids if len(set(ids))==len(ids) else None


def inspect(packet,bindings,project,input_hash,protocol_hash):
    packet=packet if isinstance(packet,dict) else {}
    bindings=bindings if isinstance(bindings,dict) else {}
    checks=[]
    def add(name,ok,evidence):
        checks.append({'name':name,'status':'PASS' if ok else 'BLOCKED','evidence':evidence})
    add('schema',packet.get('schema_version')==1,'Engineering intake schema version must equal 1.')
    add('protocol_refreeze',packet.get('protocol_state')=='REFROZEN','Current protocol amendment is not refrozen; a tag alone is insufficient without bound validation.')
    parameters=packet.get('parameters',{})
    if not isinstance(parameters,dict):
        parameters={}
    add('exact_parameter_set',set(parameters)==set(SPECS),'Unknown/missing parameter keys rejected; no defaults inserted.')
    for name,(unit,kind) in SPECS.items():
        record=parameters.get(name)
        if not isinstance(record,dict):
            add(name,False,'Missing parameter record.')
            continue
        value=record.get('value')
        if kind is float:
            valid=isinstance(value,(float,int)) and not isinstance(value,bool) and math.isfinite(value) and value>0
        else:
            valid=isinstance(value,kind) and bool(value) and finite_tree(value)
        sources=record.get('evidence',[])
        valid_sources=isinstance(sources,list) and bool(sources) and all(local_evidence(e,project) for e in sources)
        add(name,valid and record.get('unit')==unit and valid_sources,
            record.get('blocker','Invalid type/domain/unit or missing/stale local evidence; applicability needs scientific input review.'))
    design=scenario_ids(parameters.get('design_scenarios',{}).get('value')) if isinstance(parameters.get('design_scenarios'),dict) else None
    holdout=scenario_ids(parameters.get('held_out_scenarios',{}).get('value')) if isinstance(parameters.get('held_out_scenarios'),dict) else None
    add('held_out_ids',design is not None and holdout is not None and not set(design)&set(holdout),'Scenario IDs must be unique within and disjoint across design/evaluation sets; identical payload leakage requires scientific review.')
    add('input_validation_binding',bindings.get('scope')=='PRE_EXPERIMENT_INPUTS_ONLY_NOT_RESULT_VALIDATION' and bindings.get('input_sha256')==input_hash and bindings.get('protocol_sha256')==protocol_hash,
        'Input and current protocol SHA256 must match separately maintained input-validation bindings.')
    refs=bindings.get('gates',{})
    reports=[]
    commands=[]
    for gate in GATES:
        record=refs.get(gate) if isinstance(refs,dict) else None
        ok=local_evidence(record,project)
        explanation='Missing/stale gate report; three independent input checks are not configured.'
        if ok:
            path=(project/record['path']).resolve()
            reports.append(str(path))
            try:
                data=json.loads(path.read_text(encoding='utf-8'))
                commands.append(data.get('command',''))
                items=data.get('checks')
                ok=(data.get('gate')==gate and data.get('scope')=='PRE_EXPERIMENT_INPUTS_ONLY' and data.get('status')=='PASS'
                    and data.get('inputSha256')==input_hash and data.get('protocolSha256')==protocol_hash
                    and isinstance(data.get('sourceHashes'),dict) and bool(data['sourceHashes'])
                    and isinstance(data.get('command'),str) and bool(data['command'].strip())
                    and isinstance(items,list) and bool(items) and all(isinstance(c,dict) and c.get('status')=='PASS' and c.get('name') and c.get('evidence') for c in items))
                for relative,digest in data.get('sourceHashes',{}).items():
                    ok=ok and local_evidence({'path':relative,'sha256':digest},project)
                explanation='Gate report must bind live input/protocol hashes, executable command, source hashes and nonempty PASS checks; semantic independence still needs review.'
            except (ValueError,TypeError,AttributeError):
                ok=False
                explanation='Malformed input-validation report.'
        add(gate,ok,explanation)
    add('distinct_input_validators',len(reports)==3 and len(set(reports))==3 and len(commands)==3 and all(commands) and len(set(commands))==3,
        'One artifact/command cannot be reused as three different checks; different names alone do not establish scientific independence.')
    return checks


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',default='milestones/reproducibility/engineering-inputs.json')
    parser.add_argument('--bindings',default='milestones/reproducibility/engineering-validation-bindings.json')
    parser.add_argument('--report',default='milestones/reproducibility/engineering-input-gate.json')
    args=parser.parse_args()
    project=Path(__file__).resolve().parents[1]
    input_path=project/args.input
    binding_path=project/args.bindings
    protocol_path=project/'milestones/analysis-plan.md'
    packet=json.loads(input_path.read_text(encoding='utf-8'))
    bindings=json.loads(binding_path.read_text(encoding='utf-8'))
    checks=inspect(packet,bindings,project,sha(input_path),sha(protocol_path))
    report={'artifact_type':'pre_experiment_engineering_input_gate','status':'PASS_INPUT_INTAKE_ONLY' if all(c['status']=='PASS' for c in checks) else 'BLOCKED_MISSING_OR_UNVALIDATED_ENGINEERING_INPUTS',
        'scope':'NOT_OPTIMIZATION_NOT_FORMAL_RESULT_VALIDATION','codeSha256':sha(Path(__file__)),
        'inputHashes':{'engineering-inputs.json':sha(input_path),'engineering-validation-bindings.json':sha(binding_path)},
        'source_files':[{'path':str(protocol_path),'sha256':sha(protocol_path)},{'path':str(project/'milestones/protocol-amendment.md'),'sha256':sha(project/'milestones/protocol-amendment.md')}],
        'checks':checks,'blocked_count':sum(c['status']!='PASS' for c in checks),
        'limitations':['Nonempty structures are intake validation only; engineering equations, balances and case applicability require independent checks.',
            'This gate does not replace frozen-protocol approval, formal optimizer execution, or three result-hash gates.']}
    (project/args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':report['status'],'blocked_count':report['blocked_count'],'blockers':[c['name'] for c in checks if c['status']!='PASS']},indent=2))
    raise SystemExit(0 if report['status']=='PASS_INPUT_INTAKE_ONLY' else 2)


if __name__=='__main__':
    main()
