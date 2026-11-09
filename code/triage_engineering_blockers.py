"""Classify current engineering blockers by available evidence and next unlock source."""
import json
from pathlib import Path
from guard_engineering_inputs import sha

CLASSIFICATION={
'service_boundary':('EXTERNAL_OR_NATIVE_RVT','No IFC connector export; Revit host absent; PF01 identity unresolved.'),
'routing_domain':('PARTIAL_LOCAL_ONLY','Revit-local marker and geometry exist; obstacles/clearance and Archicad registration unresolved.'),
'terminal_demands':('PARTIAL_SOURCE_CONFLICT','Typed source total and schedule total both retained; service/simultaneous-demand decision unresolved.'),
'fan_curve':('EXTERNAL_REQUIRED','No PF01 pressure/efficiency/power curve; substitutions prohibited.'),
'duct_catalog':('PARTIAL_CONDITIONAL','Dimension and material evidence exist; thickness applicability, roughness and product qualification unresolved.'),
'fitting_loss_model':('EXTERNAL_REQUIRED','Route-specific coefficient evidence absent.'),
'friction_model':('PARTIAL_METHOD_ONLY','Darcy method source exists; project roughness/fluid applicability unresolved.'),
'installation_constraints':('EXTERNAL_OR_NATIVE_RVT','No certified clearance/access/bend-radius domain.'),
'velocity_limit':('EXTERNAL_REQUIRED','No applicable maximum design velocity source.'),
'material_mass_model':('PARTIAL_MATERIAL_ONLY','FeZn object associations exist; installed mass mapping absent.'),
'epd_scope_model':('PARTIAL_REFERENCE_ONLY','Reference EPD/product records exist; installed applicability and indicator boundary unresolved.'),
'equivalent_hours_per_year':('EXTERNAL_REQUIRED','No duty schedule or labelled prospective assumption frozen.'),
'analysis_horizon':('PROTOCOL_REFREEZE','No horizon frozen.'),
'replacement_rules':('EXTERNAL_REQUIRED','Component-specific lives/replacement basis absent.'),
'cost_model':('EXTERNAL_REQUIRED','Geography/year/scope prices absent.'),
'design_scenarios':('PROTOCOL_REFREEZE','Placeholder ranges inactive; source-qualified grid/tariff/product scenarios absent.'),
'held_out_scenarios':('PROTOCOL_REFREEZE','Disjoint held-out IDs/values must be frozen before optimization.'),
'solver_budget':('PROTOCOL_REFREEZE','Solver/resource/termination conditions absent.')}

if __name__=='__main__':
    project=Path(__file__).resolve().parents[1]; inp=project/'milestones/reproducibility/engineering-inputs.json'; before=sha(inp)
    data=json.loads(inp.read_text(encoding='utf-8')); rows=[]
    for name,p in data['parameters'].items():
        category,reason=CLASSIFICATION[name]
        rows.append({'parameter':name,'status':p['parameter_status'] if 'parameter_status' in p else data['parameter_status'],'classification':category,'blocker':p['blocker'],'triage_reason':reason,'evidence_count':len(p['evidence'])})
    if sha(inp)!=before: raise ValueError('Input changed')
    counts={}
    for r in rows: counts[r['classification']]=counts.get(r['classification'],0)+1
    evidence_names=('whole-IFC-connectivity-audit.json','native-RVT-runtime-preflight.json','duct-size-specification-audit.json','native-duct-material-audit.json','modelling-qualification-audit.json','fan-schedule-identity-audit.json','engineering-validation-bindings.json')
    evidence_paths=[inp]+[inp.parent/name for name in evidence_names]
    if set(data['parameters'])!=set(CLASSIFICATION): raise ValueError('Classification does not cover exact current input schema')
    report={'artifact_type':'engineering_blocker_source_triage','status':'BLOCKER_TRIAGE_ONLY','codeSha256':sha(Path(__file__)),'source_files':[{'path':str(p),'sha256':sha(p)} for p in evidence_paths],'classification_basis':'Researcher-coded evidence triage, not automated scientific applicability validation.','source_file':str(inp),'source_sha256':before,'protocol_state':data['protocol_state'],'parameter_count':len(rows),'classification_counts':counts,'parameters':rows,'selection_rule':'No class permits default parameter filling; PARTIAL classes remain blocked until source applicability and independent validation pass.','formal_experiment':False}
    out=project/'milestones/reproducibility/engineering-blocker-triage.json'; out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':report['status'],'classification_counts':counts,'parameter_count':len(rows)},ensure_ascii=True,indent=2))
