"""Explain parameter vs gate-check cardinality without populating scientific inputs."""
import json
from pathlib import Path
from guard_engineering_inputs import sha

if __name__=='__main__':
    project=Path(__file__).resolve().parents[1]; root=project/'milestones/reproducibility'
    paths={name:root/name for name in ('engineering-inputs.json','candidate-evaluation-preflight.json','engineering-parameter-unlock-checklist.json','engineering-validation-bindings.json')}
    data={name:json.loads(p.read_text(encoding='utf-8')) for name,p in paths.items()}
    packet=data['engineering-inputs.json']; pre=data['candidate-evaluation-preflight.json']; plan=data['engineering-parameter-unlock-checklist.json']
    checks=pre['result']['input_checks']; names=[c['name'] for c in checks]
    if len(names)!=len(set(names)): raise ValueError('Duplicate gate check names')
    params=set(packet['parameters']); plan_params={r['parameter'] for r in plan['parameters']}
    if params!=plan_params: raise ValueError('Unlock plan parameter coverage differs')
    if plan['input_sha256']!=sha(paths['engineering-inputs.json']) or plan['preflight_sha256']!=sha(paths['candidate-evaluation-preflight.json']): raise ValueError('Unlock plan hash stale')
    if pre['inputHashes']['engineering-inputs.json']!=sha(paths['engineering-inputs.json']): raise ValueError('Preflight input stale')
    parameter_checks=[c for c in checks if c['name'] in params]; cross_checks=[c for c in checks if c['name'] not in params]
    if len(parameter_checks)!=len(params): raise ValueError('Parameter gate coverage missing')
    gate_map={c['name']:c['status'] for c in checks}
    if any(r['gate_status']!=gate_map[r['parameter']] for r in plan['parameters']): raise ValueError('Plan/gate status differs')
    report={'artifact_type':'engineering_gate_parameter_cardinality_consistency','status':'PASS_GATE_REPORT_CONSISTENCY_ONLY','codeSha256':sha(Path(__file__)),
        'source_files':[{'path':str(p),'sha256':sha(p)} for p in paths.values()],
        'parameter_count':len(params),'gate_check_count':len(checks),'blocked_gate_check_count':sum(c['status']!='PASS' for c in checks),
        'parameter_check_count':len(parameter_checks),'cross_check_count':len(cross_checks),'cross_checks':cross_checks,
        'parameter_blocked_count':sum(c['status']!='PASS' for c in parameter_checks),'no_parameter_values_filled':all(p['value'] is None for p in packet['parameters'].values()),
        'formal_experiment':False,'limits':['This checks reporting/schema/hash agreement only, not engineering applicability.','25 blocked checks need not equal 18 missing parameters because protocol/hash/validation checks are separate.']}
    out=root/'engineering-gate-consistency-audit.json'; out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_files','cross_checks')},ensure_ascii=True,indent=2))
