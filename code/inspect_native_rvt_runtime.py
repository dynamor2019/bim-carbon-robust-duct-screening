"""Bounded runtime prerequisites for native RVT connector extraction; no model opened."""
import json,os
from pathlib import Path
from guard_engineering_inputs import sha

if __name__=='__main__':
    project=Path(__file__).resolve().parents[1]
    paths=[Path('C:/Program Files/Autodesk')/f'Revit {year}' for year in (2023,2024,2025,2026)]
    checks=[{'directory':str(p),'host_exists':(p/'Revit.exe').is_file(),'api_exists':(p/'RevitAPI.dll').is_file()} for p in paths]
    revit_command=[str(Path(directory)/'Revit.exe') for directory in os.environ.get('PATH','').split(os.pathsep) if directory and (Path(directory)/'Revit.exe').is_file()]
    ready=any(c['host_exists'] and c['api_exists'] for c in checks)
    report={'artifact_type':'native_RVT_extraction_prerequisite_screen','status':'HOST_DISCOVERED_REQUIRES_API_EXECUTION_VALIDATION' if ready else 'BLOCKED_NO_HOST_IN_CHECKED_STANDARD_PATHS',
        'codeSha256':sha(Path(__file__)),'checked_standard_paths':checks,'PATH_host_matches':revit_command,'native_model_opened':False,'connector_extraction_executed':False,
        'limitations':['Checked standard installation paths and PATH only; no claim of exhaustive machine software inventory.',
            'API assembly alone would not establish usable licensed host or model/version compatibility.',
            'Revit 2024 source model declared; source-compatible host and read-only API invocation required.'], 'formal_experiment':False}
    (project/'milestones/reproducibility/native-RVT-runtime-preflight.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps(report,indent=2))
