"""Machine-recorded software verification only; never formal BIM experiment output."""
import json
import subprocess
import sys
from pathlib import Path
from guard_engineering_inputs import sha


def main():
    project=Path(__file__).resolve().parents[1]
    command=[sys.executable,'-X','utf8','-m','unittest','discover','-s','code','-p','test_finite_candidate_decisions.py','-v']
    run=subprocess.run(command,cwd=project,text=True,capture_output=True,encoding='utf-8')
    result={'artifact_type':'finite_candidate_decision_software_verification','status':'PASS_SOFTWARE_FIXTURES_ONLY' if run.returncode==0 else 'FAIL_SOFTWARE_VERIFICATION',
        'codeSha256':sha(Path(__file__)),'helperHashes':{'guard_engineering_inputs.py':sha(Path(__file__).with_name('guard_engineering_inputs.py'))},
        'source_files':[{'path':str(p),'sha256':sha(p)} for p in (project/'code/finite_candidate_decisions.py',project/'code/test_finite_candidate_decisions.py')],
        'command':command,'returncode':run.returncode,'stdout':run.stdout,'stderr':run.stderr,
        'engineering_data_used':False,'formal_experiment':False,
        'limitations':['Finite supplied-candidate optima are not global route optima; candidate completeness, physics and engineering input validity are unverified.',
            'Arithmetic fixtures including independent nested-loop comparison are not independent recomputation of BIM carbon results.']}
    (project/'milestones/reproducibility/finite-decision-software-audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':result['status'],'returncode':run.returncode,'formal_experiment':False},indent=2))
    raise SystemExit(run.returncode)


if __name__=='__main__':
    main()
