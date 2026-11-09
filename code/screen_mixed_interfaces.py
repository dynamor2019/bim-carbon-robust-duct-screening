"""Match source-sized rectangular boundaries, retaining covers and all ambiguity."""
import json
import math
import re
from pathlib import Path
import numpy as np
from recover_rectangular_interfaces import rectangles
from recover_fitting_interfaces import sha


def rectangle_match(a,b,tolerance=1e-5):
    if math.dist(a['center_m'],b['center_m'])>tolerance:
        return None
    dot=abs(np.array(a['normal_sign_arbitrary'])@np.array(b['normal_sign_arbitrary']))
    angle=math.degrees(math.acos(float(np.clip(dot,0,1))))
    if angle>.01:
        return None
    distance=np.linalg.norm(np.array(a['corners_m'])[:,None,:]-np.array(b['corners_m'])[None,:,:],axis=2)
    residual=float(max(distance.min(axis=0).max(),distance.min(axis=1).max()))
    if residual>tolerance:
        return None
    return {'center_gap_m':math.dist(a['center_m'],b['center_m']),'corner_hausdorff_m':residual,'normal_angle_deg':angle}


def main():
    project=Path(__file__).resolve().parents[1]
    folder=project/'milestones/reproducibility/network-interfaces'
    models=[]
    hashes={}
    for material in ['concrete','timber']:
        path=folder/(material+'-interfaces.json')
        hashes[path.name]=sha(path)
        data=json.loads(path.read_text(encoding='utf-8'))
        components=[]
        ports=[]
        for record in data['components']:
            geom=record.get('psets',{}).get('FI_Geometria',{})
            size_text=' '.join(str(geom.get(key,'')) for key in ['Liitoskoko (DU)','Koko (DU)'])
            if not re.search(r'\d+\s*[xX×]\s*\d+',size_text) and not (geom.get('Leveys') and geom.get('Korkeus')):
                continue
            review=rectangles(record)
            sizes=[sorted([float(a)/1000,float(b)/1000]) for a,b in re.findall(r'(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)',size_text)]
            qualified=[]
            for index,boundary in enumerate(review['rectangular_boundaries']):
                compatible=boundary['matches_raw_width_height_mm_candidate'] or any(max(abs(x-y) for x,y in zip(sorted(boundary['edge_lengths_m']),size))<=1e-5 for size in sizes)
                if not compatible:
                    continue
                qualified.append({'boundary_id':f"{record['ifc_id']}:rect:{index}",'ifc_id':record['ifc_id'],
                    'name':record['name'],'ifc_type':record['ifc_type'],'source_raw_flow':record['psets'].get('FI_Tekninen',{}).get('Virtaama'),
                    'source_name_indicates_cap':'tulppa' in record['name'].lower(),**boundary})
            circle_ports=[p for p in data['candidate_ports'] if p['ifc_id']==record['ifc_id']]
            components.append({'ifc_id':record['ifc_id'],'guid':record['guid'],'name':record['name'],'ifc_type':record['ifc_type'],
                'source_geometry':geom,'source_raw_flow':record['psets'].get('FI_Tekninen',{}).get('Virtaama'),
                'qualified_rectangular_boundaries':qualified,'circular_candidate_ports':circle_ports,
                'all_rectangle_count':len(review['rectangular_boundaries']),'nonmanifold_edges':review['nonmanifold_edges']})
            ports.extend(qualified)
        matches=[]
        for i,a in enumerate(ports):
            for b in ports[i+1:]:
                if a['ifc_id']==b['ifc_id']:
                    continue
                comparison=rectangle_match(a,b)
                if comparison is not None:
                    matches.append({'a':a['boundary_id'],'b':b['boundary_id'],'component_a':a['ifc_id'],'component_b':b['ifc_id'],
                        **comparison,'involves_named_cap':a['source_name_indicates_cap'] or b['source_name_indicates_cap'],
                        'status':'GEOMETRIC_RECTANGLE_MATCH_ONLY; not_physical_edge'})
        degree={p['boundary_id']:sum(m['a']==p['boundary_id'] or m['b']==p['boundary_id'] for m in matches) for p in ports}
        models.append({'model_id':data['model_id'],'components':components,'matches':matches,
            'boundary_match_counts':degree,'summary':{'rectangular_size_components':len(components),'source_sized_boundaries':len(ports),
                'numerical_matches':len(matches),'unmatched':sum(d==0 for d in degree.values()),'ambiguous':sum(d>1 for d in degree.values()),
                'mixed_shape_components':sum(bool(c['qualified_rectangular_boundaries'] and c['circular_candidate_ports']) for c in components)}})
    result={'artifact_type':'source_sized_mixed_section_interface_screen','status':'REQUIRES_ENGINEERING_REVIEW',
        'inputHashes':hashes,'codeSha256':sha(Path(__file__)),'geometryHelperSha256':sha(Path(__file__).with_name('recover_rectangular_interfaces.py')),
        'models':models,'criteria':{'center_and_corner_m':1e-5,'normal_deg':.01},
        'limitations':['Corner Hausdorff comparison checks in-plane rotation; sorted dimensions alone are insufficient.',
            'Named caps are retained and flagged; their two surfaces are not both assigned flow ports.',
            'Mixed circular/rectangular features within one component do not certify internal flow passage.',
            'No edges inserted, direction assigned, source flows altered, or engineering joint tolerance adopted.']}
    (folder/'mixed-section-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps([{'model_id':m['model_id'],'summary':m['summary'],
        'components':[{'id':c['ifc_id'],'name':c['name'],'rectangles':len(c['qualified_rectangular_boundaries']),
            'circles':len(c['circular_candidate_ports']),'raw_flow':c['source_raw_flow']} for c in m['components']],
        'matches':m['matches']} for m in models],ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
