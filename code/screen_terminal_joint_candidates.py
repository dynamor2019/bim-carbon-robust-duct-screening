"""Screen URH mating candidates using source-qualified NS versus D dimensions.
No port coordinates/radii are changed and no mechanical connection certified.
"""
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    project=Path(__file__).resolve().parents[1]
    folder=project/'milestones/reproducibility/network-interfaces'
    dimension_path=folder/'terminal-dimension-review.json'
    dimension_data=json.loads(dimension_path.read_text(encoding='utf-8'))
    dims={r['nominal_size_mm']:r for r in dimension_data['manufacturer_dimension_rows']}
    hashes={dimension_path.name:sha(dimension_path)}
    reports=[]
    for material in ['concrete','timber']:
        path=folder/(material+'-interfaces.json')
        hashes[path.name]=sha(path)
        data=json.loads(path.read_text(encoding='utf-8'))
        components={r['ifc_id']:r for r in data['components']}
        ports=data['candidate_ports']
        per_component={}
        for p in ports:
            per_component.setdefault(p['ifc_id'],[]).append(p)
        records=[]
        counts=Counter()
        for record in data['components']:
            name=record.get('name','')
            match=re.fullmatch(r'URH/([A-Z])-(\d+)',name)
            if record['ifc_type']!='IfcAirTerminal' or not match or int(match.group(2)) not in dims:
                continue
            if record['psets'].get('FI_Tuote',{}).get('Tuotetyypin valmistaja','').lower()!='halton':
                continue
            dimension=dims[int(match.group(2))]
            nominal_r=dimension['nominal_size_mm']/2000
            valve_r=dimension['D_mm']/2000
            terminal_ports=[p for p in per_component.get(record['ifc_id'],[]) if any(min(abs(r-valve_r),abs(r-nominal_r))<=1e-5 for r in p['radii_m'])]
            candidates=[]
            for terminal in terminal_ports:
                for peer in ports:
                    if peer['ifc_type'] not in ('IfcDuctSegment','IfcDuctFitting','IfcDamper','IfcDuctSilencer') or peer['ifc_id']==record['ifc_id']:
                        continue
                    if not any(abs(r-nominal_r)<=1e-5 for r in peer['radii_m']):
                        continue
                    delta=[b-a for a,b in zip(terminal['center_m'],peer['center_m'])]
                    distance=math.sqrt(sum(v*v for v in delta))
                    if distance>.1:
                        continue
                    normal=terminal['normal_sign_arbitrary']
                    axial=sum(v*n for v,n in zip(delta,normal))
                    transverse=math.sqrt(max(0.,distance*distance-axial*axial))
                    dot=abs(sum(a*b for a,b in zip(normal,peer['normal_sign_arbitrary'])))
                    angle=math.degrees(math.acos(min(1.,max(0.,dot))))
                    if transverse<=1e-5 and angle<=.01:
                        terminal_q=record['psets'].get('FI_Tekninen',{}).get('Virtaama')
                        peer_q=components[peer['ifc_id']].get('psets',{}).get('FI_Tekninen',{}).get('Virtaama')
                        flow_difference=float(peer_q)-float(terminal_q) if isinstance(peer_q,(int,float)) and isinstance(terminal_q,(int,float)) else None
                        candidates.append({'terminal_port':terminal['port_id'],'peer_port':peer['port_id'],
                            'peer_ifc_id':peer['ifc_id'],'peer_ifc_type':peer['ifc_type'],
                            'terminal_raw_flow':terminal_q,'peer_raw_flow':peer_q,'raw_flow_difference':flow_difference,
                            'center_gap_m':distance,'axial_offset_sign_arbitrary_m':axial,
                            'transverse_gap_m':transverse,'axis_angle_deg':angle,
                            'nominal_radius_m':nominal_r,'manufacturer_D_radius_m':valve_r,
                            'terminal_ring_size_basis':'IFC_NOMINAL_SIZE_RING' if any(abs(r-nominal_r)<=1e-5 for r in terminal['radii_m']) else 'CURRENT_MANUFACTURER_D_RING',
                            'numerically_coincident_centers':distance<=1e-5,
                            'status':'SOURCE_SIZE_COMPATIBLE_GEOMETRIC_CANDIDATE; installation_frame_and_model_version_unverified'})
            candidate_peers={c['peer_ifc_id'] for c in candidates}
            coincident_peers={c['peer_ifc_id'] for c in candidates if c['numerically_coincident_centers']}
            category='NO_COLLINEAR_SOURCE_SIZE_CANDIDATE'
            if len(coincident_peers)==1:
                category='ONE_COINCIDENT_SOURCE_SIZE_CANDIDATE_ONLY'
            elif len(coincident_peers)>1:
                category='AMBIGUOUS_COINCIDENT_CANDIDATES'
            elif candidate_peers:
                category='AXIALLY_OFFSET_CANDIDATES_REQUIRE_FRAME_EVIDENCE'
            counts[category]+=1
            records.append({'ifc_id':record['ifc_id'],'guid':record['guid'],'name':name,
                'classification':category,'manufacturer_nominal_mm':dimension['nominal_size_mm'],
                'manufacturer_D_mm':dimension['D_mm'],'candidates':sorted(candidates,key=lambda c:(c['center_gap_m'],c['peer_ifc_id']))})
        nearest=[r['candidates'][0] for r in records if r['candidates']]
        reports.append({'model_id':data['model_id'],'counts':dict(counts),'terminal_records':records,
            'peer_component_count_distribution':dict(Counter(len({c['peer_ifc_id'] for c in r['candidates']}) for r in records)),
            'nearest_candidate_center_gap_range_m':[min(c['center_gap_m'] for c in nearest),max(c['center_gap_m'] for c in nearest)] if nearest else None,
            'nearest_candidate_raw_flow_screen':dict(Counter('missing' if c['raw_flow_difference'] is None else 'equal' if abs(c['raw_flow_difference'])<=1e-9 else 'unequal' for c in nearest)),
            'search_window_m':.1,'window_scope':'Diagnostic search only; not an allowed joint offset or approved frame length.'})
    result={'status':'REQUIRES_INSTALLATION_AND_VERSION_REVIEW','artifact_type':'source_dimension_mating_candidate_screen',
        'inputHashes':hashes,'codeSha256':sha(Path(__file__)),'models':reports,
        'decision':'No generic radius tolerance expanded; no endpoint shifted; no candidate inserted into hydraulic graph.'}
    (folder/'terminal-joint-candidates.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps([{'model_id':r['model_id'],'counts':r['counts'],
        'peer_component_count_distribution':r['peer_component_count_distribution'],
        'nearest_gap_range_m':r['nearest_candidate_center_gap_range_m'],
        'nearest_candidate_raw_flow_screen':r['nearest_candidate_raw_flow_screen'],
        'example_records':r['terminal_records'][:3]} for r in reports],ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
