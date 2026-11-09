"""Controlled evaluator scaffolding; not a formal experiment entry or complete feasibility solver."""
import json
from pathlib import Path
from guard_engineering_inputs import inspect,sha
from candidate_edge_evidence import authorize
from candidate_tree_flow import validate_tree
from candidate_pressure_loss import segment_loss,path_requirements
from candidate_fan_curve import screen_curve


def evaluate_authorized_arithmetic(case):
    """Internal software-testable stage composition; upstream provenance gate is separate.
    This function cannot return full engineering feasibility or carbon objectives.
    """
    stages=[]
    try:
        tree=validate_tree(case['nodes'],case['edges'],case['root'],case['terminal_demands_m3_s'],case['maximum_velocity_m_s'])
        stages.append({'name':'tree_flow_velocity','status':tree['status'],'result':tree})
        if tree['status']!='PASS_TREE_FLOW_AND_VELOCITY_ONLY':
            return {'status':'FAIL_CANDIDATE_VELOCITY','stages':stages,'engineering_feasible':None}
        loss_records={}
        edge_map={e['id']:e for e in case['edges']}
        physics=case['edge_physics']
        if set(physics)!=set(edge_map):
            raise ValueError('Every edge needs explicit pressure inputs; extras rejected')
        local_ids=[]
        for row in tree['edges']:
            eid=row['edge_id']
            edge=edge_map[eid]
            params=physics[eid]
            local_ids.extend(r['id'] for r in params['local_losses'])
            loss_records[eid]=segment_loss(row['flow_m3_s'],edge['length_m'],edge['diameter_m'],params['density_kg_m3'],params['darcy_factor'],params['local_losses'],params['friction_ref'])
        if len(set(local_ids))!=len(local_ids):
            raise ValueError('Local loss IDs duplicate across edges; repeated physical burden allocation is not allowed')
        stages.append({'name':'edge_pressure_arithmetic','status':'PASS_ARITHMETIC_ONLY','result':loss_records})
        paths=path_requirements(tree['terminal_paths'],{eid:r['total_pressure_loss_Pa'] for eid,r in loss_records.items()},case['terminal_boundary_losses_Pa'],case['root_boundary_loss_Pa'])
        stages.append({'name':'path_pressure_arithmetic','status':'PASS_ARITHMETIC_ONLY','result':paths})
        fan=screen_curve(case['fan_curve'],tree['terminal_total_m3_s'],paths['maximum_path_requirement_Pa'],case['pressure_basis'],case['fan_conditions'])
        stages.append({'name':'fixed_curve_screen','status':fan['status'],'result':fan})
        # No guessed hours, motor efficiency, fan/system intersection or EPD assignment.
        return {'status':'BLOCKED_OPERATING_POINT_AND_BALANCE_UNCERTIFIED' if fan['status']=='PASS_FIXED_CURVE_CAPACITY_SCREEN_ONLY' else 'FAIL_FIXED_CURVE_SCREEN',
            'stages':stages,'engineering_feasible':None,'objective_cost':None,'carbon_ledger_executed':False,
            'reason':'Fixed-speed capacity screen is not a certified system equilibrium; no power-to-energy or carbon conversion performed.'}
    except (ValueError,KeyError,TypeError,OverflowError) as error:
        return {'status':'BLOCKED_INVALID_OR_MISSING_STAGE_INPUT','stages':stages,'engineering_feasible':None,'objective_cost':None,
            'carbon_ledger_executed':False,'error':str(error)}


def evaluate_case(case,packet,bindings,project,input_hash,protocol_hash):
    checks=inspect(packet,bindings,project,input_hash,protocol_hash)
    if any(c['status']!='PASS' for c in checks):
        return {'status':'BLOCKED_ENGINEERING_INPUT_GATE','input_checks':checks,'engineering_feasible':None,
            'stages':[],'physics_executed':False,'carbon_ledger_executed':False}
    if not isinstance(case,dict) or not isinstance(case.get('edges'),list) or not isinstance(case.get('edge_evidence'),dict):
        return {'status':'BLOCKED_MISSING_AUTHORIZED_CASE','engineering_feasible':None,'stages':[],'physics_executed':False}
    edge_results=[]
    authorized=[]
    for edge in case['edges']:
        result=authorize(edge,case['edge_evidence'].get(edge.get('id')),project)
        edge_results.append({'id':edge.get('id'),'result':result})
        if result['authorized_edge'] is not None:
            authorized.append(result['authorized_edge'])
    if len(authorized)!=len(case['edges']):
        return {'status':'BLOCKED_EDGE_EVIDENCE','engineering_feasible':None,'edge_checks':edge_results,'stages':[],
            'physics_executed':False,'carbon_ledger_executed':False}
    result=evaluate_authorized_arithmetic(dict(case,edges=authorized))
    result.update(input_checks=checks,edge_checks=edge_results,physics_executed=True)
    return result


def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'milestones/reproducibility'
    packet_path=root/'engineering-inputs.json'
    binding_path=root/'engineering-validation-bindings.json'
    protocol_path=project/'milestones/analysis-plan.md'
    packet=json.loads(packet_path.read_text(encoding='utf-8'))
    bindings=json.loads(binding_path.read_text(encoding='utf-8'))
    result=evaluate_case(None,packet,bindings,project,sha(packet_path),sha(protocol_path))
    report={'artifact_type':'controlled_candidate_evaluation_preflight','status':result['status'],'result':result,
        'codeSha256':sha(Path(__file__)),
        'helperHashes':{name:sha(Path(__file__).with_name(name)) for name in ('guard_engineering_inputs.py','candidate_edge_evidence.py','candidate_tree_flow.py','candidate_pressure_loss.py','candidate_fan_curve.py')},
        'inputHashes':{packet_path.name:sha(packet_path),binding_path.name:sha(binding_path)},
        'source_files':[{'path':str(protocol_path),'sha256':sha(protocol_path)}],
        'formal_experiment':False,'limitations':['Controlled preflight/scaffolding only; no case is manufactured when actual packet is blocked.',
            'Arithmetic composition does not solve operating point, balancing controls, source applicability or provide full optimization evaluations.']}
    (root/'candidate-evaluation-preflight.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':result['status'],'physics_executed':result.get('physics_executed',False),
        'blocker_count':sum(c['status']!='PASS' for c in result.get('input_checks',[])),'formal_experiment':False},indent=2))
    raise SystemExit(2 if result['status'].startswith('BLOCKED') else 0)


if __name__=='__main__':
    main()
