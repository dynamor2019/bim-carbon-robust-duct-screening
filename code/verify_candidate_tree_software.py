"""Record actual tree-flow software tests without binding a formal experiment."""
import json
import subprocess
import sys
from pathlib import Path
from guard_engineering_inputs import sha


def main():
    project=Path(__file__).resolve().parents[1]
    command=[sys.executable,'-X','utf8','-m','unittest','discover','-s','code','-p','test_candidate_*.py','-v']
    run=subprocess.run(command,cwd=project,text=True,capture_output=True,encoding='utf-8')
    report={'artifact_type':'candidate_tree_flow_software_verification','status':'PASS_SOFTWARE_FIXTURES_ONLY' if run.returncode==0 else 'FAIL_SOFTWARE_VERIFICATION',
        'codeSha256':sha(Path(__file__)),'helperHashes':{'guard_engineering_inputs.py':sha(Path(__file__).with_name('guard_engineering_inputs.py'))},
        'source_files':[{'path':str(p),'sha256':sha(p)} for p in (project/'code/candidate_tree_flow.py',project/'code/test_candidate_tree_flow.py',project/'code/candidate_edge_evidence.py',project/'code/test_candidate_edge_evidence.py',project/'code/candidate_pressure_loss.py',project/'code/test_candidate_pressure_loss.py',project/'.dsh-state/literature-cache/NIST-TN-2206.pdf',project/'.dsh-state/literature-cache/NIST-TN-2206.txt',project/'code/candidate_fan_curve.py',project/'code/test_candidate_fan_curve.py',project/'.dsh-state/literature-cache/AMCA-straightening-fan-curves.html',project/'code/candidate_carbon_ledger.py',project/'code/test_candidate_carbon_ledger.py',project/'code/qualify_halton_epd.py',project/'code/evaluate_candidate_design.py',project/'code/test_candidate_evaluation.py',project/'code/candidate_operating_point.py',project/'code/test_candidate_operating_point.py',project/'code/candidate_quadratic_balance.py',project/'code/test_candidate_quadratic_balance.py',project/'code/candidate_network_fan.py',project/'code/test_candidate_network_fan.py')],
        'command':command,'returncode':run.returncode,'stdout':run.stdout,'stderr':run.stderr,
        'engineering_data_used':False,'formal_experiment':False,
        'limitations':['Supplied directed tree only; authorization flags require independently hash-bound source evidence upstream.',
            'Explicit pressure-loss arithmetic is tested, but no solved pressure balance, fan capacity, installation certification, physical flow direction or carbon result exists.']}
    (project/'milestones/reproducibility/candidate-tree-software-audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':report['status'],'returncode':run.returncode,'formal_experiment':False},indent=2))
    raise SystemExit(run.returncode)


if __name__=='__main__':
    main()
