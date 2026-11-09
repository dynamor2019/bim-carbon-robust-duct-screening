"""Independent raw-mesh projection checks; no feasible-domain or physics claim."""
import hashlib
import json
from pathlib import Path
import numpy as np


def main():
    p=Path(__file__).resolve().parent.parent;r=p/'milestones/reproducibility'
    frozen=r/'local-spatial-domain-freeze.json'
    d=json.loads(frozen.read_text(encoding='utf-8'));s=d['selected_source'];mesh=Path(s['mesh_path'])
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    with np.load(mesh,allow_pickle=False) as f:v=f['vertices'];faces=f['faces']
    a=np.array(s['end_a_m']);b=np.array(s['end_b_m']);delta=b-a;length=float(np.linalg.norm(delta));direction=delta/length
    axial=(v-a)@direction;radial=np.linalg.norm(v-a-axial[:,None]*direction,axis=1)
    radius=d['sections'][0]['outer_diameter_m']/2
    tolerance=1e-5  # Existing candidate inventory numerical-nearness scale, not construction tolerance.
    values={'mesh_projection_length_m':float(axial.max()-axial.min()),'source_endpoint_distance_m':length,
        'mesh_max_radial_distance_m':float(radial.max()),'source_outer_radius_m':radius,
        'axial_min_m':float(axial.min()),'axial_max_m':float(axial.max()),
        'vertex_count':len(v),'face_count':len(faces),'comparison_tolerance_m':tolerance}
    checks=[{'name':'mesh_hash_binding','status':'PASS' if sha(mesh)==s['mesh_sha256'] else 'FAIL','evidence':sha(mesh)},
        {'name':'finite_mesh_arrays','status':'PASS' if np.isfinite(v).all() and v.ndim==2 and v.shape[1]==3 else 'FAIL','evidence':'vertices must be finite xyz'},
        {'name':'mesh_projection_matches_frozen_axis','status':'PASS' if abs(float(axial.min()))<=tolerance and abs(float(axial.max())-length)<=tolerance else 'FAIL','evidence':str(values)},
        {'name':'mesh_radius_matches_frozen_section','status':'PASS' if abs(float(radial.max())-radius)<=tolerance else 'FAIL','evidence':str(values)},
        {'name':'source_roi_contains_raw_mesh','status':'PASS' if np.all(v.min(axis=0)>=np.array(d['roi']['bbox_min_m'])-tolerance) and np.all(v.max(axis=0)<=np.array(d['roi']['bbox_max_m'])+tolerance) else 'FAIL','evidence':'raw vertex extrema against frozen ROI'},
        {'name':'main_unknowns_not_promoted','status':'PASS' if not d['main_analysis']['ready_for_contract_binding'] and not d['main_analysis']['candidates'] else 'FAIL','evidence':'domain main-analysis remains empty; geometry verification cannot certify service or space'}]
    report={'artifact_type':'independent_local_source_mesh_arithmetic_audit',
        'status':'PASS_LOCAL_MESH_ARITHMETIC_ONLY' if all(x['status']=='PASS' for x in checks) else 'FAIL',
        'codeSha256':sha(Path(__file__)),'source_files':[{'path':str(f),'sha256':sha(f)} for f in [frozen,mesh]],
        'checks':checks,'values':values,'scope':'One source extrusion; independent mesh arithmetic not scientific qualification of routing domain',
        'formal_experiment':False,'numpy_version':np.__version__}
    (r/'local-spatial-mesh-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'values':values,'failed':[x['name'] for x in checks if x['status']=='FAIL']},indent=2))
    raise SystemExit(0 if all(x['status']=='PASS' for x in checks) else 1)


if __name__=='__main__':main()
