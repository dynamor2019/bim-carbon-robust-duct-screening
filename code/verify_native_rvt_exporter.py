"""Audit connector validator fixtures and exporter syntax, never host functionality."""
import ast,json,subprocess,sys
from pathlib import Path
from guard_engineering_inputs import sha

if __name__=='__main__':
    project=Path(__file__).resolve().parents[1]
    exporter=project/'code/export_native_rvt_connectors.py'
    ast.parse(exporter.read_text(encoding='utf-8'))
    command=[sys.executable,'-X','utf8','-m','unittest','discover','-s','code','-p','test_native_rvt_connectors.py','-v']
    run=subprocess.run(command,cwd=project,text=True,capture_output=True,encoding='utf-8')
    files=[exporter,project/'code/validate_native_rvt_connectors.py',project/'code/test_native_rvt_connectors.py',project/'milestones/reproducibility/native-RVT-runtime-preflight.json']
    report={'artifact_type':'native_RVT_connector_exporter_preparation','status':'PASS_VALIDATOR_FIXTURES_AND_SYNTAX_ONLY' if run.returncode==0 else 'FAIL_SOFTWARE_TESTS',
        'codeSha256':sha(Path(__file__)),'source_files':[{'path':str(p),'sha256':sha(p)} for p in files],
        'command':command,'returncode':run.returncode,'stderr':run.stderr,'stdout':run.stdout,
        'exporter_host_executed':False,'real_connector_records':0,'formal_experiment':False,
        'limitations':['CPython AST syntax check does not validate IronPython or Autodesk API bindings.','No real host extraction, RVT/IFC mapping or service validation performed.']}
    (project/'milestones/reproducibility/native-RVT-exporter-software-audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':report['status'],'returncode':run.returncode,'exporter_host_executed':False},indent=2)); raise SystemExit(run.returncode)
