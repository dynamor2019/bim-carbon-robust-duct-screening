"""Bounded local registration evidence from explicitly named unequal-axis alignment pieces."""
import itertools,json
from pathlib import Path
import numpy as np
from recover_fitting_interfaces import sha


def compare(architecture,hvac,tolerance=1e-6):
    a,b=architecture['geometry'],hvac['geometry']
    bounds_gap=float(np.max(np.abs(np.array([a['min_m'],a['max_m']])-np.array([b['min_m'],b['max_m']]))))
    dimensions=np.array(a['max_m'])-a['min_m']
    distinct_dimensions=bool(np.min(np.diff(np.sort(dimensions)))>tolerance)
    corners=np.array(list(itertools.product(*zip(a['min_m'],a['max_m']))))
    vertices=np.array(b['unique_vertices_m'])
    corner_gap=float(np.linalg.norm(corners[:,None,:]-vertices[None,:,:],axis=2).min(axis=1).max())
    passed=bounds_gap<=tolerance and corner_gap<=tolerance and distinct_dimensions
    return {'status':'PASS_LOCAL_MARKER_COORDINATES_ONLY' if passed else 'FAIL_LOCAL_MARKER_COORDINATES',
        'bbox_gap_m':bounds_gap,'maximum_corner_nearest_vertex_gap_m':corner_gap,'architecture_marker_dimensions_m':dimensions.tolist(),
        'unequal_axis_lengths':distinct_dimensions,'tolerance_m':tolerance,
        'limitations':['Eight-decimal vertex memo precision used; original unrounded bbox bounds retained.',
            'Agreement tests explicit marker location and unequal-axis extents, not all building geometry or projected map conversion.',
            'Decorative glyph vertices are retained; full Hausdorff equivalence is not claimed.']}


def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'milestones/reproducibility'
    path=root/'alignment-marker-review.json'
    data=json.loads(path.read_text(encoding='utf-8'))
    pairs=[]
    for hvac in (m for m in data['models'] if m['discipline']=='hvac'):
        h=[hit for hit in hvac['marker_hits'] if 'SHARED_Alignment_Cube' in (hit['name'] or '')]
        for architecture in (m for m in data['models'] if m['discipline']=='architecture' and ('Timber' in m['source'])==('Timber' in hvac['source'])):
            a=[hit for hit in architecture['marker_hits'] if 'Kohdistuskappale' in (hit['name'] or '')]
            result=compare(a[0],h[0]) if len(a)==1 and len(h)==1 else {'status':'UNSUPPORTED_NO_UNIQUE_EXPLICIT_MARKER_PAIR'}
            pairs.append({'architecture':architecture['source'],'hvac':hvac['source'],'architecture_marker_count':len(a),'hvac_marker_count':len(h),
                'pairing_basis':'Explicit alignment product labels plus original world-coordinate unequal-axis bounding geometry; not GUID match.',
                'architecture_marker_id':a[0]['id'] if len(a)==1 else None,'hvac_marker_id':h[0]['id'] if len(h)==1 else None,'comparison':result})
    report={'artifact_type':'explicit_local_alignment_piece_registration_check','status':'LOCAL_MARKER_EVIDENCE_ONLY',
        'inputHashes':{path.name:sha(path)},'codeSha256':sha(Path(__file__)),'pairs':pairs,
        'limitations':['Revit marker agreement can support unchanged local coordinates but does not resolve Archicad map-origin discrepancy.',
            'Single-origin marker does not test off-origin deformation, storey representation differences, room boundaries or service assignments.',
            'No inferred corrective translation or rotation applied.']}
    (root/'alignment-registration-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps(report,ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
