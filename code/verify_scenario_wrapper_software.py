"""Record scenario wrapper software verification only."""
import json,subprocess,sys
from pathlib import Path
from guard_engineering_inputs import sha
from evaluate_candidate_design import evaluate_case


def main():
    project=Path(__file__).resolve().parents[1]
    command=[sys.executable,'-X','utf8','-m','unittest','discover','-s','code','-p','test_scenario_evaluation.py','-v']
    run=subprocess.run(command,cwd=project,text=True,capture_output=True,encoding='utf-8')
    input_path=project/'milestones/reproducibility/engineering-inputs.json'
    bindings_path=project/'milestones/reproducibility/engineering-validation-bindings.json'
    protocol_path=project/'milestones/analysis-plan.md'
    current=evaluate_case(None,json.loads(input_path.read_text(encoding='utf-8')),json.loads(bindings_path.read_text(encoding='utf-8')),project,sha(input_path),sha(protocol_path))
    report={'artifact_type':'scenario_evaluation_wrapper_software_verification','status':'PASS_SOFTWARE_FIXTURES_ONLY' if run.returncode==0 else 'FAIL_SOFTWARE_VERIFICATION','codeSha256':sha(Path(__file__)),
        'source_files':[{'path':str(p),'sha256':sha(p)} for p in (project/'code/scenario_evaluation.py',project/'code/test_scenario_evaluation.py',project/'code/finite_candidate_decisions.py',project/'code/evaluate_candidate_design.py',project/'code/guard_engineering_inputs.py',input_path,bindings_path,protocol_path)],
        'current_engineering_preflight':{'status':current['status'],'physics_executed':current.get('physics_executed',False),'blocked_count':sum(c['status']!='PASS' for c in current.get('input_checks',[]))},'command':command,'returncode':run.returncode,'stdout':run.stdout,'stderr':run.stderr,'engineering_data_used':False,'formal_experiment':False,
        'limitations':['Scenario complete/selection flags are software contracts, not engineering validity; runner output still requires source-qualified evaluator.',
            'Hash binding detects mismatch but cannot prove the semantic correctness of an unchanged input.']}
    (project/'milestones/reproducibility/scenario-wrapper-software-audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':report['status'],'returncode':run.returncode,'formal_experiment':False},indent=2)); raise SystemExit(run.returncode)

if __name__=='__main__': main()
