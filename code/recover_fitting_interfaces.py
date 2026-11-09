"""Recover candidate circular end rims from verified source mesh caches; no native ports."""
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def boundary_loops(faces):
    edge_faces=defaultdict(list)
    for index,face in enumerate(faces):
        for a,b in [(face[0],face[1]),(face[1],face[2]),(face[2],face[0])]:
            edge_faces[tuple(sorted((int(a),int(b))))].append(index)
    edges=[e for e,owners in edge_faces.items() if len(owners)==1]
    adjacency=defaultdict(set)
    for a,b in edges:
        adjacency[a].add(b)
        adjacency[b].add(a)
    remaining=set(adjacency)
    loops=[]
    rejected=[]
    while remaining:
        root=min(remaining)
        todo=[root]
        group=set()
        while todo:
            n=todo.pop()
            if n in group:
                continue
            group.add(n)
            todo.extend(adjacency[n]-group)
        remaining-=group
        if any(len(adjacency[n])!=2 for n in group):
            rejected.append({'vertex_count':len(group),'reason':'not_a_degree_two_closed_loop'})
            continue
        # Circle fitting is order independent; preserve source vertex IDs.
        loops.append(sorted(group))
    return loops,rejected,sum(len(owners)>2 for owners in edge_faces.values())


def circle_fit(points):
    if len(points)<8 or not np.isfinite(points).all():
        return None
    origin=points.mean(axis=0)
    _,_,axes=np.linalg.svd(points-origin,full_matrices=False)
    normal=axes[-1]
    plane_error=float(np.max(abs((points-origin)@normal)))
    if plane_error>1e-6:
        return None
    xy=(points-origin)@axes[:2].T
    matrix=np.column_stack((2*xy[:,0],2*xy[:,1],np.ones(len(xy))))
    estimate,_,rank,_=np.linalg.lstsq(matrix,np.sum(xy*xy,axis=1),rcond=None)
    if rank<3:
        return None
    center_xy=estimate[:2]
    radius_squared=float(estimate[2]+center_xy@center_xy)
    if radius_squared<=0:
        return None
    radius=math.sqrt(radius_squared)
    residual=float(np.max(abs(np.linalg.norm(xy-center_xy,axis=1)-radius)))
    if residual>1e-5:
        return None
    return {'center_m':(origin+center_xy@axes[:2]).tolist(),'normal_sign_arbitrary':normal.tolist(),
            'radius_m':radius,'point_count':len(points),'plane_error_max_m':plane_error,
            'radial_residual_max_m':residual}


def weld(vertices,faces):
    # Numerical vertex welding only; this is not a connection distance.
    _,indices,inverse=np.unique(np.rint(vertices/1e-8).astype(np.int64),axis=0,return_index=True,return_inverse=True)
    new_faces=inverse[faces]
    keep=(new_faces[:,0]!=new_faces[:,1])&(new_faces[:,1]!=new_faces[:,2])&(new_faces[:,0]!=new_faces[:,2])
    return vertices[indices],new_faces[keep]


def planar_patches(vertices,faces):
    triangles=vertices[faces]
    vectors=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    lengths=np.linalg.norm(vectors,axis=1)
    normals=np.zeros_like(vectors)
    valid=lengths>1e-14
    normals[valid]=vectors[valid]/lengths[valid,None]
    edges=defaultdict(list)
    for i,face in enumerate(faces):
        if not valid[i]:
            continue
        for a,b in [(face[0],face[1]),(face[1],face[2]),(face[2],face[0])]:
            edges[tuple(sorted((int(a),int(b))))].append(i)
    adjacency=defaultdict(set)
    for owners in edges.values():
        if len(owners)!=2:
            continue
        a,b=owners
        if abs(float(normals[a]@normals[b]))>=1-1e-10:
            adjacency[a].add(b)
            adjacency[b].add(a)
    remaining=set(np.flatnonzero(valid).tolist())
    patches=[]
    while remaining:
        root=min(remaining)
        todo=[root]
        group=set()
        while todo:
            i=todo.pop()
            if i in group:
                continue
            group.add(i)
            todo.extend(adjacency[i]-group)
        remaining-=group
        if len(group)>=6:
            patches.append(sorted(group))
    return patches


def recover_rims(vertices,faces):
    vertices,faces=weld(vertices,faces)
    loops,rejected,nonmanifold=boundary_loops(faces)
    candidates=[]
    for loop in loops:
        fitted=circle_fit(vertices[loop])
        if fitted:
            candidates.append({**fitted,'origin':'whole_mesh_boundary','vertex_ids':loop})
    for patch_id,patch in enumerate(planar_patches(vertices,faces)):
        patch_loops,_,_=boundary_loops(faces[patch])
        for loop in patch_loops:
            fitted=circle_fit(vertices[loop])
            if fitted:
                candidates.append({**fitted,'origin':'planar_patch_boundary','patch_index':patch_id,'vertex_ids':loop})
    unique=[]
    for candidate in sorted(candidates,key=lambda r:(r['center_m'],r['radius_m'])):
        if not any(np.linalg.norm(np.array(candidate['center_m'])-np.array(r['center_m']))<1e-6
                   and abs(candidate['radius_m']-r['radius_m'])<1e-6 for r in unique):
            unique.append(candidate)
    return {'rims':unique,'welded_vertex_count':len(vertices),'triangle_count':len(faces),
            'whole_mesh_loop_count':len(loops),'rejected_whole_mesh_loops':rejected,
            'nonmanifold_edge_count':nonmanifold,
            'evidence_limit':'Circular mesh rims are geometry candidates; inner/outer rims may belong to one interface. No native ports, flow direction or connectivity certified.'}


def main():
    project=Path(__file__).resolve().parents[1]
    folder=project/'milestones/reproducibility/boundary-evidence'
    source=folder/'paired-boundary-geometry.json'
    boundary=json.loads(source.read_text(encoding='utf-8'))
    sources={source.name:sha(source)}
    reports=[]
    for model in boundary['models']:
        fittings=[r for r in model['selected_entities'] if r['ifc_type']=='IfcDuctFitting']
        ducts=[r for r in model['selected_entities'] if r['ifc_type']=='IfcDuctSegment']
        for fitting in fittings:
            info=fitting['mesh_cache']
            path=Path(info['path'])
            digest=sha(path)
            if digest!=info['sha256']:
                raise ValueError('Stale mesh cache: '+str(path))
            sources[str(path)]=digest
            with np.load(path,allow_pickle=False) as mesh:
                recovered=recover_rims(mesh['vertices'],mesh['faces'])
            comparisons=[]
            for ring_index,ring in enumerate(recovered['rims']):
                center=np.array(ring['center_m'])
                normal=np.array(ring['normal_sign_arbitrary'])
                for duct in ducts:
                    for axis in duct.get('profile_extrusion_axes',[]):
                        direction=np.array(axis['end_b_m'])-np.array(axis['end_a_m'])
                        direction/=np.linalg.norm(direction)
                        alignment=math.degrees(math.acos(float(np.clip(abs(direction@normal),0,1))))
                        diameter=duct['pilot_nominal_diameter_m']
                        for end in ['end_a_m','end_b_m']:
                            gap=float(np.linalg.norm(center-np.array(axis[end])))
                            comparisons.append({'ring_index':ring_index,'duct_id':duct['ifc_id'],'duct_end':end,
                                'center_distance_m':gap,'axis_normal_angle_deg':alignment,
                                'nominal_radius_difference_m':abs(diameter/2-ring['radius_m']) if diameter else None,
                                'feature_match_status': 'NUMERIC_FEATURE_MATCH_ONLY' if gap<=1e-5 and alignment<=.01 and diameter and abs(diameter/2-ring['radius_m'])<=1e-5 else 'NUMERIC_FEATURES_DO_NOT_MATCH',
                                'evidence_level':'geometric_comparison_only_not_confirmed_service_or_connection'})
            reports.append({'model_id':model['model_id'],'fitting_id':fitting['ifc_id'],'fitting_guid':fitting['guid'],
                'recovered':recovered,'duct_end_comparisons':sorted(comparisons,key=lambda r:(r['center_distance_m'],r['duct_id'])),
                'status':'CANDIDATE_RIMS_ONLY' if recovered['rims'] else 'NO_SUPPORTED_RIMS_FOUND'})
    result={'artifact_type':'mesh_fitting_interface_diagnostic','status':'REQUIRES_REVIEW',
            'codeSha256':sha(Path(__file__)),'sourceHashes':sources,
            'numerical_fit_tolerances_m':{'vertex_weld':1e-8,'plane':1e-6,'radial_fit':1e-5},
            'numerical_feature_match_criteria':{'center_m':1e-5,'radius_m':1e-5,'axis_normal_angle_deg':.01},
            'tolerance_scope':'Numerical geometry diagnostics, not approved engineering joint tolerances.', 'fittings':reports}
    out=folder/'fitting-interface-review.json'
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps([{'model':r['model_id'],'fitting':r['fitting_id'],'status':r['status'],
        'rim_count':len(r['recovered']['rims']), 'nonmanifold_edges':r['recovered']['nonmanifold_edge_count'],
        'rims':[{k:x[k] for k in ['center_m','radius_m','origin']} for x in r['recovered']['rims']],
        'best_comparison_per_duct':[min((x for x in r['duct_end_comparisons'] if x['duct_id']==duct_id),key=lambda x:x['center_distance_m'])
            for duct_id in sorted({x['duct_id'] for x in r['duct_end_comparisons']})]} for r in reports],ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
