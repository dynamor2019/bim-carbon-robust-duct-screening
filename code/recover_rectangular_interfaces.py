"""Recover rectangular mesh boundaries and inspect URH rim/mesh-plane offsets.
All output is geometric evidence, not native ports or certified physical connections.
"""
import json
import math
import re
from collections import defaultdict,Counter
from pathlib import Path
import numpy as np
from recover_fitting_interfaces import weld,boundary_loops,sha


def planar_groups(vertices,faces):
    triangles=vertices[faces]
    vectors=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    lengths=np.linalg.norm(vectors,axis=1)
    valid=lengths>1e-14
    normals=np.zeros_like(vectors)
    normals[valid]=vectors[valid]/lengths[valid,None]
    edges=defaultdict(list)
    for index,face in enumerate(faces):
        if valid[index]:
            for a,b in ((face[0],face[1]),(face[1],face[2]),(face[2],face[0])):
                edges[tuple(sorted((int(a),int(b))))].append(index)
    adjacency=defaultdict(set)
    for owners in edges.values():
        if len(owners)==2:
            a,b=owners
            if abs(normals[a]@normals[b])>=1-1e-10:
                adjacency[a].add(b)
                adjacency[b].add(a)
    remaining=set(np.flatnonzero(valid).tolist())
    groups=[]
    while remaining:
        stack=[min(remaining)]
        seen=set()
        while stack:
            node=stack.pop()
            if node not in seen:
                seen.add(node)
                stack.extend(adjacency[node]-seen)
        remaining-=seen
        groups.append(sorted(seen))
    return groups


def hull(points):
    ordered=sorted(set(tuple(p) for p in points))
    if len(ordered)<3:
        return []
    def cross(a,b,c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    lower=[]
    for point in ordered:
        while len(lower)>=2 and cross(lower[-2],lower[-1],point)<=1e-12:
            lower.pop()
        lower.append(point)
    upper=[]
    for point in reversed(ordered):
        while len(upper)>=2 and cross(upper[-2],upper[-1],point)<=1e-12:
            upper.pop()
        upper.append(point)
    return lower[:-1]+upper[:-1]


def rectangle_fit(points):
    if len(points)<4 or not np.isfinite(points).all():
        return None
    origin=points.mean(axis=0)
    _,_,axes=np.linalg.svd(points-origin,full_matrices=False)
    plane_error=float(np.max(abs((points-origin)@axes[-1])))
    if plane_error>1e-6:
        return None
    xy=(points-origin)@axes[:2].T
    corners=np.array(hull(xy))
    if len(corners)!=4:
        return None
    edges=np.roll(corners,-1,axis=0)-corners
    lengths=np.linalg.norm(edges,axis=1)
    if min(lengths)<=1e-6:
        return None
    units=edges/lengths[:,None]
    if max(abs(units[i]@units[(i+1)%4]) for i in range(4))>1e-6:
        return None
    if max(abs(lengths[0]-lengths[2]),abs(lengths[1]-lengths[3]))>1e-6:
        return None
    distances=[]
    for point in xy:
        candidates=[]
        for i in range(4):
            edge=edges[i]
            t=float(np.clip((point-corners[i])@edge/(edge@edge),0,1))
            candidates.append(np.linalg.norm(point-corners[i]-t*edge))
        distances.append(min(candidates))
    residual=float(max(distances))
    if residual>1e-6:
        return None
    world=origin+corners@axes[:2]
    return {'center_m':world.mean(axis=0).tolist(),'corners_m':world.tolist(),
        'normal_sign_arbitrary':axes[-1].tolist(),'edge_lengths_m':[float(lengths[0]),float(lengths[1])],
        'plane_residual_max_m':plane_error,'boundary_residual_max_m':residual,
        'status':'RECTANGULAR_BOUNDARY_NOT_CERTIFIED_OPENING_OR_PORT'}


def mesh(record):
    path=Path(record['mesh_path'])
    if sha(path)!=record['mesh_sha256']:
        raise ValueError('Mesh cache hash mismatch: '+str(path))
    with np.load(path,allow_pickle=False) as data:
        return weld(data['vertices'],data['faces'])


def declared_circle_fit(points,radius):
    # Source DU-constrained screen for coarse closed polygons, not a generic port detector.
    if len(points)<6 or not np.isfinite(points).all():
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
    fitted=math.sqrt(squared)
    residual=float(np.max(abs(np.linalg.norm(xy-estimate[:2],axis=1)-fitted)))
    if abs(fitted-radius)>1e-5 or residual>1e-5:
        return None
    return {'center_m':(origin+estimate[:2]@axes[:2]).tolist(),'normal_sign_arbitrary':axes[-1].tolist(),
        'radius_m':fitted,'source_DU_radius_m_candidate':radius,'point_count':len(points),
        'plane_residual_max_m':plane_error,'radial_residual_max_m':residual,
        'status':'DU_SIZE_CONSISTENT_POLYGON_CANDIDATE; not_native_port'}


def rectangles(record):
    vertices,faces=mesh(record)
    loops,_,nonmanifold=boundary_loops(faces)
    candidates=[]
    circles=[]
    du=str(record.get('psets',{}).get('FI_Geometria',{}).get('Liitoskoko (DU)',''))
    round_size=re.fullmatch(r'[Øø](\d+(?:\.\d+)?)',du)
    expected_radius=float(round_size.group(1))/2000 if round_size else None
    for loop in loops:
        fit=rectangle_fit(vertices[loop])
        if fit:
            candidates.append({**fit,'origin':'whole_mesh_boundary'})
    for index,group in enumerate(planar_groups(vertices,faces)):
        patch_loops,_,_=boundary_loops(faces[group])
        for loop in patch_loops:
            if expected_radius:
                circle=declared_circle_fit(vertices[loop],expected_radius)
                if circle:
                    circles.append({**circle,'patch_index':index,'triangle_count':len(group)})
            fit=rectangle_fit(vertices[loop])
            if fit:
                candidates.append({**fit,'origin':'planar_patch_boundary','patch_index':index})
    unique=[]
    for candidate in candidates:
        if not any(np.linalg.norm(np.array(candidate['center_m'])-np.array(old['center_m']))<=1e-6
            and max(abs(a-b) for a,b in zip(sorted(candidate['edge_lengths_m']),sorted(old['edge_lengths_m'])))<=1e-6
            and abs(np.array(candidate['normal_sign_arbitrary'])@np.array(old['normal_sign_arbitrary']))>=1-1e-10 for old in unique):
            unique.append(candidate)
    geom=record.get('psets',{}).get('FI_Geometria',{})
    width=geom.get('Leveys')
    height=geom.get('Korkeus')
    expected=sorted([float(width)/1000,float(height)/1000]) if width and height else None
    declared_rectangles=[sorted([float(a)/1000,float(b)/1000]) for a,b in re.findall(r'(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)',str(geom.get('Liitoskoko (DU)','')))]
    for candidate in unique:
        candidate['matches_raw_width_height_mm_candidate']=bool(expected and max(abs(a-b) for a,b in zip(sorted(candidate['edge_lengths_m']),expected))<=1e-5)
        candidate['matches_declared_DU_rectangle_mm_candidate']=any(max(abs(a-b) for a,b in zip(sorted(candidate['edge_lengths_m']),du))<=1e-5 for du in declared_rectangles)
    return {'declared_round_boundary_candidates':circles,'expected_source_DU_radius_m_candidate':expected_radius,
        'declared_DU_rectangles_m_candidate':declared_rectangles,'ifc_id':record['ifc_id'],'guid':record['guid'],'name':record['name'],'ifc_type':record['ifc_type'],
        'nonmanifold_edges':nonmanifold,'expected_width_height_m_candidate':expected,'rectangular_boundaries':unique,
        'status':'GEOMETRIC_REVIEW_REQUIRED' if unique else 'NO_RECTANGULAR_BOUNDARY_RECOVERED'}


def urh_plane_review(record,port,peer):
    vertices,faces=mesh(record)
    center=np.array(port['center_m'])
    normal=np.array(port['normal_sign_arbitrary'])
    peer_center=np.array(peer['center_m'])
    projections=(vertices-center)@normal
    peer_projection=float((peer_center-center)@normal)
    plane_candidates=[]
    for group in planar_groups(vertices,faces):
        points=vertices[np.unique(faces[group])]
        tri=vertices[faces[group[0]]]
        vector=np.cross(tri[1]-tri[0],tri[2]-tri[0])
        vector/=np.linalg.norm(vector)
        if abs(vector@normal)<1-1e-10:
            continue
        projection=float((points.mean(axis=0)-center)@normal)
        plane_candidates.append({'triangle_count':len(group),'plane_offset_from_ring_m':projection,
            'peer_distance_to_plane_m':abs(peer_projection-projection),
            'plane_offset_scope':'Unbounded supporting plane; not evidence of an opening containing the pipe axis'})
    return {'ifc_id':record['ifc_id'],'guid':record['guid'],'name':record['name'],
        'rim_port_id':port['port_id'],'diagnostic_peer_port_id':peer['port_id'],
        'rim_to_peer_axial_offset_abs_m':abs(peer_projection),
        'mesh_projection_span_m':float(projections.max()-projections.min()),
        'peer_to_closest_mesh_extreme_projection_m':min(abs(peer_projection-projections.min()),abs(peer_projection-projections.max())),
        'closest_parallel_patch_plane':min(plane_candidates,key=lambda p:p['peer_distance_to_plane_m']) if plane_candidates else None,
        'status':'NO_CONNECTOR_ASSIGNED; extrema_and_supporting_planes_are_not_installation_ports'}


def main():
    project=Path(__file__).resolve().parents[1]
    folder=project/'milestones/reproducibility/network-interfaces'
    joint_path=folder/'terminal-joint-candidates.json'
    joints=json.loads(joint_path.read_text(encoding='utf-8'))
    hashes={joint_path.name:sha(joint_path)}
    reports=[]
    for material,joint_model in zip(['concrete','timber'],joints['models']):
        path=folder/(material+'-interfaces.json')
        hashes[path.name]=sha(path)
        data=json.loads(path.read_text(encoding='utf-8'))
        if data['model_id']!=joint_model['model_id']:
            raise ValueError('Model pairing mismatch')
        records={r['ifc_id']:r for r in data['components']}
        ports={p['port_id']:p for p in data['candidate_ports']}
        reviews=[rectangles(r) for r in records.values() if not r.get('features') and r['status']!='EXTRACTION_FAILED']
        plane_reviews=[]
        for terminal in joint_model['terminal_records']:
            if not terminal['candidates']:
                continue
            candidate=terminal['candidates'][0]
            plane_reviews.append(urh_plane_review(records[terminal['ifc_id']],ports[candidate['terminal_port']],ports[candidate['peer_port']]))
        gaps=[r['peer_to_closest_mesh_extreme_projection_m'] for r in plane_reviews]
        spans=[r['mesh_projection_span_m'] for r in plane_reviews]
        reports.append({'model_id':data['model_id'],'uncovered_component_reviews':reviews,'URH_plane_reviews':plane_reviews,
            'summary':{'reviewed_uncovered_components':len(reviews),'with_rectangular_boundaries':sum(bool(r['rectangular_boundaries']) for r in reviews),
                'URH_reviewed':len(plane_reviews),'mesh_axis_span_range_m':[min(spans),max(spans)],
                'nearest_mesh_extreme_gap_range_m':[min(gaps),max(gaps)],
                'status':'GEOMETRIC_FEATURES_ONLY; physical_topology_gate_remains_blocked'}})
    result={'artifact_type':'rectangle_and_terminal_plane_audit','status':'REQUIRES_ENGINEERING_REVIEW',
        'inputHashes':hashes,'codeSha256':sha(Path(__file__)),'helperSha256':sha(Path(__file__).with_name('recover_fitting_interfaces.py')),
        'models':reports,'limitations':['All rectangular surface boundaries retained, including covers and enclosure faces.',
            'URH nearest candidate used solely for offset diagnostics; other candidates retained in original ledger.',
            'No mesh extreme or unbounded supporting plane is assigned as a connector.']}
    (folder/'rectangular-interface-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps([{'model_id':r['model_id'],'summary':r['summary'],
        'uncovered':[{'ifc_id':x['ifc_id'],'name':x['name'],'rectangle_count':len(x['rectangular_boundaries']),
            'declared_size_round_candidates':len(x['declared_round_boundary_candidates']),
            'declared_DU_rectangles_m_candidate':x['declared_DU_rectangles_m_candidate'],
            'DU_matched_rectangles':sum(y['matches_declared_DU_rectangle_mm_candidate'] for y in x['rectangular_boundaries']),
            'raw_size_matched_rectangles':sum(y['matches_raw_width_height_mm_candidate'] for y in x['rectangular_boundaries'])} for x in r['uncovered_component_reviews']],
        'example_URH_plane':r['URH_plane_reviews'][0]} for r in reports],ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
