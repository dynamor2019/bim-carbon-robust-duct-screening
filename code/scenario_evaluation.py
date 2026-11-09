"""Scenario-set execution wrapper; blocked results stay visible and are not selectable."""
import math
import re
import copy
import hashlib
import json
from pathlib import Path
from finite_candidate_decisions import Evaluation


def sha_obj(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def run_scenarios(candidate_ids,scenario_records,run_one):
    if not isinstance(candidate_ids,list) or not candidate_ids or len(set(candidate_ids))!=len(candidate_ids):
        raise ValueError('Unique nonempty candidate IDs required')
    if not all(isinstance(x,str) and x.strip() for x in candidate_ids):
        raise ValueError('Candidate IDs must be nonempty strings')
    if not isinstance(scenario_records,list) or not scenario_records:
        raise ValueError('Nonempty frozen scenario records required')
    scenario_ids=[]
    for scenario in scenario_records:
        if not isinstance(scenario,dict) or not isinstance(scenario.get('id'),str) or not scenario['id'].strip() or scenario['id'] in scenario_ids:
            raise ValueError('Scenario IDs must be unique nonempty strings')
        if not isinstance(scenario.get('input_sha256'),str) or not re.fullmatch(r'[0-9a-f]{64}',scenario['input_sha256']):
            raise ValueError('Scenario input hash required')
        scenario_ids.append(scenario['id'])
    results={cid:{} for cid in candidate_ids}
    records=[]
    for scenario in scenario_records:
        sid=scenario['id']
        expected_hash=scenario['input_sha256']
        for cid in candidate_ids:
            frozen_record_hash=sha_obj(scenario)
            output=run_one(cid,copy.deepcopy(scenario))
            if sha_obj(scenario)!=frozen_record_hash:
                raise ValueError('Frozen scenario record changed during evaluation')
            if not isinstance(output,dict):
                raise ValueError('Scenario runner must return typed record')
            observed_hash=output.get('input_sha256')
            if observed_hash!=expected_hash:
                results[cid][sid]=Evaluation(False,None)
                records.append({'candidate':cid,'scenario':sid,'status':'BLOCKED_INPUT_HASH_MISMATCH','expected_input_sha256':expected_hash,'observed_input_sha256':observed_hash})
                continue
            status=output.get('status')
            validated=output.get('engineering_validation')=='VERIFIED_FOR_CURRENT_INPUT'
            feasible=validated and output.get('engineering_feasible') is True
            known_infeasible=validated and output.get('engineering_feasible') is False
            cost=output.get('objective_cost')
            if feasible and (isinstance(cost,bool) or not isinstance(cost,(int,float)) or not math.isfinite(cost)):
                raise ValueError('Feasible result requires finite numeric objective cost')
            if known_infeasible and cost is not None:
                raise ValueError('Validated infeasible objective must be null')
            results[cid][sid]=Evaluation(feasible,cost if feasible else None)
            records.append({'candidate':cid,'scenario':sid,'status':'PASS_FEASIBLE' if feasible else ('VERIFIED_INFEASIBLE' if known_infeasible else 'BLOCKED_UNVERIFIED'),
                'runner_status':status,'input_sha256':observed_hash,'objective_cost':cost if feasible else None,'runner_record':output})
    complete=all(all(s in results[c] for s in scenario_ids) for c in candidate_ids)
    qualified=all(r['status'] in ('PASS_FEASIBLE','VERIFIED_INFEASIBLE') for r in records)
    return {'status':'PASS_COMPLETE_SCENARIO_EVALUATION' if complete and qualified else 'BLOCKED_UNVERIFIED_SCENARIO_EVALUATION',
        'scenario_ids':scenario_ids,'candidate_ids':candidate_ids,'results':results,'records':records,
        'all_candidates_all_scenarios_complete':complete,'selection_allowed':complete and qualified,
        'input_hashes':{s['id']:s['input_sha256'] for s in scenario_records},
        'scope':'SCENARIO_WRAPPER_ONLY; DOES_NOT_CERTIFY_ENGINEERING_MODEL'}
