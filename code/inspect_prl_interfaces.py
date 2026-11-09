"""Inspect PRL assembly polygons using source nominal and verified manufacturer dimensions.
Cyclic quadrilaterals are explicitly ambiguous, not native circular ports.
"""
import json
import math
import re
from pathlib import Path
import numpy as np
from recover_rectangular_interfaces import mesh,planar_groups
from recover_fitting_interfaces import boundary_loops,sha


def cyclic_polygon(points):
    if len(points)<4 or not np.isfinite(points).all():
        return None
    origin=points.mean(axis=0)
    _,_,axes=np.linalg.svd(points-origin,full_matrices=False)
    plane_error=float(np.max(abs((points-origin)@axes[-1])))
    if plane_error>1e-6:
        return None
    xy=(points-origin)@axes[:2].T
    matrix=np.column_stack((2*xy,np.ones(len(points))))
    estimate,_,rank,_=np.linalg.lstsq(matrix,np.sum(xy*xy,axis=1),rcond=None)
    squared=estimate[2]+estimate[:2]@estimate[:2]
    if rank<3 or squared<=0:
        return None
    radius=math.sqrt(squared)
    residual=float(np.max(abs(np.linalg.norm(xy-estimate[:2],axis=1)-radius)))
    if residual>1e-5:
        return None
    angles=np.sort(np.arctan2((xy-estimate[:2])[:,1],(xy-estimate[:2])[:,0]))
    increments=np.diff(np.r_[angles,angles[0]+2*np.pi])
    if len(points)==4 and np.max(abs(increments-np.pi/2))>1e-5:
        return None
    return {'center_m':(origin+estimate[:2]@axes[:2]).tolist(),'normal_sign_arbitrary':axes[-1].tolist(),
        'radius_m':radius,'point_count':len(points),'radial_residual_max_m':residual,'plane_residual_max_m':plane_error,
        'geometry_limit':'Cyclic square may represent a coarse circular symbol or an actual square face; source semantics needed.' if len(points)==4 else 'Cyclic polygon is not native circular connector.'}


def main():
    project=Path(__file__).resolve().parents[1]
    parameters=project/'milestones/reproducibility/parameter-evidence'
    product_path=parameters/'halton-prl-source.json'
    product=json.loads(product_path.read_text(encoding='utf-8'))
    dimension_header=next(row for row in product['table_rows'] if row and row[0]=='NS')
    dimensions={row[0]:dict(zip(dimension_header,row)) for row in product['table_rows'] if row and '×' in row[0] and len(row)==len(dimension_header)}
    models={row[0]:row for row in product['table_rows'] if row and re.fullmatch(r'PRL/[A-I]',row[0])}
    hashes={product_path.name:sha(product_path)}
    reports=[]
    for material in ['concrete','timber']:
        path=project/'milestones/reproducibility/network-interfaces'/(material+'-interfaces.json')
        hashes[path.name]=sha(path)
        data=json.loads(path.read_text(encoding='utf-8'))
        terminals=[]
        for record in data['components']:
            match=re.fullmatch(r'AHD-(\d+)-(\d+)\+PRL/([A-I])-(\d+)-(\d+)-(\d+)',record.get('name',''))
            if not match or record['ifc_type']!='IfcAirTerminal':
                continue
            width,height,variant,pwidth,pheight,nominal=match.groups()
            key=pwidth+'×'+pheight
            if key not in dimensions or 'PRL/'+variant not in models:
                raise ValueError('Assembly dimension/model not covered by extracted source')
            nominal_radius=float(nominal)/2000
            manufacturer_radius=float(dimensions[key]['D'])/2000
            vertices,faces=mesh(record)
            candidates=[]
            loop_histogram={}
            for group in planar_groups(vertices,faces):
                loops,_,_=boundary_loops(faces[group])
                for loop in loops:
                    loop_histogram[str(len(loop))]=loop_histogram.get(str(len(loop)),0)+1
                    fitted=cyclic_polygon(vertices[loop])
                    if fitted is None:
                        continue
                    basis=[]
                    if abs(fitted['radius_m']-nominal_radius)<=1e-5:
                        basis.append('IFC_NOMINAL_DIAMETER')
                    if abs(fitted['radius_m']-manufacturer_radius)<=1e-5:
                        basis.append('CURRENT_MANUFACTURER_D')
                    if not basis:
                        continue
                    if any(np.linalg.norm(np.array(fitted['center_m'])-np.array(old['center_m']))<=1e-6 and abs(fitted['radius_m']-old['radius_m'])<=1e-6 for old in candidates):
                        continue
                    fitted['size_basis']=basis
                    peers=[]
                    for peer in data['candidate_ports']:
                        if peer['ifc_id']==record['ifc_id'] or peer['ifc_type'] not in ('IfcDuctSegment','IfcDuctFitting'):
                            continue
                        if not any(abs(r-nominal_radius)<=1e-5 for r in peer['radii_m']):
                            continue
                        dot=abs(np.array(fitted['normal_sign_arbitrary'])@np.array(peer['normal_sign_arbitrary']))
                        angle=math.degrees(math.acos(float(np.clip(dot,0,1))))
                        distance=math.dist(fitted['center_m'],peer['center_m'])
                        if angle<=.01 and distance<=.1:
                            peers.append({'port_id':peer['port_id'],'ifc_id':peer['ifc_id'],'center_gap_m':distance,
                                'axis_angle_deg':angle,'status':'SOURCE_SIZE_CANDIDATE_ONLY'})
                    fitted['nearby_aligned_peers']=sorted(peers,key=lambda p:p['center_gap_m'])
                    candidates.append(fitted)
            terminals.append({'ifc_id':record['ifc_id'],'guid':record['guid'],'name':record['name'],
                'source_connection_size':record['psets']['FI_Geometria'].get('Liitoskoko (DU)'),
                'manufacturer_dimension_row':dimensions[key],'manufacturer_model_row':models['PRL/'+variant],
                'planar_loop_point_count_histogram':loop_histogram,'size_qualified_cyclic_polygons':candidates,
                'status':'GEOMETRIC_APPROXIMATION_REQUIRES_REVIEW' if candidates else 'NO_SIZE_QUALIFIED_CYCLIC_POLYGON'})
        reports.append({'model_id':data['model_id'],'terminals':terminals,
            'summary':{'assembly_terminal_count':len(terminals),'with_size_qualified_cyclic_polygons':sum(bool(t['size_qualified_cyclic_polygons']) for t in terminals)}})
    result={'artifact_type':'manufacturer_qualified_PRL_geometry_screen','status':'REQUIRES_ENGINEERING_REVIEW',
        'inputHashes':hashes,'codeSha256':sha(Path(__file__)),'geometryHelperSha256':sha(Path(__file__).with_name('recover_rectangular_interfaces.py')),
        'models':reports,'limitations':['Current dimensions not proof of exact 2024 product version.',
            'Cyclic square is ambiguous; no native connector created, no source geometry changed.',
            '0.1 m is a diagnostic search window, not allowed joint offset.']}
    (parameters/'prl-interface-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps(reports,ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
