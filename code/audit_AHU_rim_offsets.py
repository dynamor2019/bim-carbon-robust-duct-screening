"""Report all compatible-radius circular rim offsets to touching AHU duct candidates."""
import json,math
from pathlib import Path
import numpy as np
from recover_fitting_interfaces import sha


def offsets(fan_features,pipe_features):
    pairs=[]
    for i,a in enumerate(fan_features):
        for j,b in enumerate(pipe_features):
            radius_gap=min(abs(x-y) for x in a['radii_m'] for y in b['radii_m'])
            cosine=float(np.clip(abs(np.array(a['normal_sign_arbitrary'])@b['normal_sign_arbitrary']),0,1))
            angle=math.degrees(math.acos(cosine))
            if radius_gap>1e-5 or angle>.01:
                continue
            delta=np.array(b['center_m'])-a['center_m']
            pairs.append({'AHU_feature_index':i,'pipe_feature_index':j,'delta_xyz_m':delta.tolist(),'center_gap_m':float(np.linalg.norm(delta)),
                'radius_gap_m':float(radius_gap),'normal_angle_deg':angle,'strict_numerical_center_match':bool(np.linalg.norm(delta)<=1e-5)})
    return sorted(pairs,key=lambda r:(r['center_gap_m'],r['AHU_feature_index'],r['pipe_feature_index']))


def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'milestones/reproducibility'
    path=root/'AHU-neighborhood-interface-audit.json'
    data=json.loads(path.read_text(encoding='utf-8'))
    models=[]
    for model in data['models']:
        candidates=[]
        for record in model['records']:
            if record['type']!='IfcDuctSegment' or record['bbox_gap_to_AHU_m']>1e-5:
                continue
            rows=offsets(model['fan_candidate_features'],record['candidate_features'])
            candidates.append({'id':record['ifc_id'],'guid':record['guid'],'groups':[g['group_name'] for g in record['groups']],
                'raw_flow':record['psets'].get('FI_Tekninen',{}).get('Virtaama'),'compatible_circle_offsets':rows,
                'nearest_compatible_gap_m':rows[0]['center_gap_m'] if rows else None,'strict_match_count':sum(r['strict_numerical_center_match'] for r in rows)})
        models.append({'source':model['source'],'AHU_id':model['fan_id'],'touching_bbox_duct_candidates':candidates})
    report={'artifact_type':'all_radius_normal_compatible_AHU_duct_circle_offsets','status':'CIRCULAR_OFFSET_DIAGNOSIS_ONLY',
        'inputHashes':{path.name:sha(path)},'codeSha256':sha(Path(__file__)),'models':models,
        'limitations':['Closest compatible feature is reported descriptively, not selected as a physical port.',
            'All compatible feature offsets retained; no tolerance relaxation or inferred adapter/corrective offset.',
            'Circle and arbitrary-normal agreement does not determine flow sign, topology or service.']}
    (root/'AHU-rim-offset-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'models':[{'source':m['source'],'candidates':[{'id':r['id'],'groups':r['groups'],'raw_flow':r['raw_flow'],
        'nearest_gap_m':r['nearest_compatible_gap_m'],'strict_matches':r['strict_match_count'],'nearest_offset':r['compatible_circle_offsets'][0] if r['compatible_circle_offsets'] else None} for r in m['touching_bbox_duct_candidates']]} for m in models]},ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
