"""Verify preserved frozen text and hash-bind its documented, not-refrozen amendment."""
import json
from pathlib import Path
from guard_engineering_inputs import sha


def main():
    project=Path(__file__).resolve().parents[1]
    original=project/'.dsh-state/protocol-freeze/analysis-plan-original.md'
    current=project/'milestones/analysis-plan.md'
    amendment=project/'milestones/protocol-amendment.md'
    packet=project/'milestones/reproducibility/engineering-inputs.json'
    gate=project/'milestones/reproducibility/engineering-input-gate.json'
    old=original.read_text(encoding='utf-8-sig')
    now=current.read_text(encoding='utf-8-sig')
    packet_data=json.loads(packet.read_text(encoding='utf-8'))
    gate_data=json.loads(gate.read_text(encoding='utf-8'))
    checks=[
        {'name':'original_frozen_text_preserved','status':'PASS' if now.endswith(old) else 'FAIL','evidence':'Canonical protocol retains exact historical text after an explicit amendment-status header; original bytes saved separately.'},
        {'name':'refreeze_not_claimed','status':'PASS' if packet_data['protocol_state']=='REFREEZE_PENDING' and 'NOT REFROZEN' in amendment.read_text(encoding='utf-8') else 'FAIL','evidence':'Amendment documentation is not a refrozen protocol or approval.'},
        {'name':'engineering_run_stopped','status':'PASS' if gate_data['status']=='BLOCKED_MISSING_OR_UNVALIDATED_ENGINEERING_INPUTS' else 'FAIL','evidence':'Original real engineering intake remains blocked; no original physical optimizer was invoked. Separate registered synthetic execution is outside this check.'},
        {'name':'hypotheses_and_baselines_unchanged','status':'PASS' if now.endswith(old) else 'FAIL','evidence':'All original H1-H4 and Section6 methods remain in unchanged historical body; no original engineering outcomes exist. Synthetic method results do not test these original carbon hypotheses.'}
    ]
    paths=[original,current,amendment,packet,gate]
    report={'artifact_type':'documented_protocol_amendment_and_original_freeze_binding','status':'PASS_AMENDMENT_DOCUMENTATION_ONLY' if all(c['status']=='PASS' for c in checks) else 'FAIL_AMENDMENT_BINDING',
        'codeSha256':sha(Path(__file__)),'unitHelperSha256':None,
        'source_files':[{'path':str(p),'sha256':sha(p)} for p in paths],
        'helperHashes':{'guard_engineering_inputs.py':sha(Path(__file__).with_name('guard_engineering_inputs.py'))},
        'originalFreezeSha256':sha(original),'currentProtocolSha256':sha(current),'amendmentSha256':sha(amendment),
        'checks':checks,'formal_experiment':'ORIGINAL_REAL_ENGINEERING_BLOCKED','scope':'ORIGINAL_REAL_ENGINEERING_DOCUMENTATION_ONLY','limitations':['Documentation check is not scientific certification, refreeze approval, or result validation.']}
    report.pop('unitHelperSha256')
    path=project/'milestones/reproducibility/protocol-amendment-binding.json'
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':report['status'],'originalFreezeSha256':report['originalFreezeSha256'],'checks':checks},indent=2))
    if any(c['status']=='FAIL' for c in checks):
        raise SystemExit(1)


if __name__=='__main__':
    main()
