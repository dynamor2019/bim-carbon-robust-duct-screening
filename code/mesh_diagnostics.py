"""Diagnose tessellation edge subdivisions and nearest boundary; never modify source mesh."""
from collections import Counter,defaultdict
import numpy as np


def edge_subdivision_audit(vertices,faces,tolerance=1e-8):
    vertices=np.asarray(vertices,float)
    faces=np.asarray(faces,int)
    _,indices,inverse=np.unique(np.round(vertices,8),axis=0,return_index=True,return_inverse=True)
    points=vertices[indices]
    original=Counter()
    refined=Counter()
    winding=defaultdict(int)
    splits=[]
    for face in inverse[faces]:
        for a,b in zip(face,np.roll(face,-1)):
            a,b=int(a),int(b)
            original[tuple(sorted((a,b)))]+=1
            vector=points[b]-points[a]
            length2=float(vector@vector)
            if length2<=tolerance**2:
                continue
            parameter=((points-points[a])@vector)/length2
            distance=np.linalg.norm(points-(points[a]+parameter[:,None]*vector),axis=1)
            interior=np.flatnonzero((distance<=tolerance)&(parameter>tolerance/np.sqrt(length2))&(parameter<1-tolerance/np.sqrt(length2)))
            sequence=[a]+sorted(interior.tolist(),key=lambda i:parameter[i])+[b]
            if len(sequence)>2:
                splits.append({'from':points[a].tolist(),'to':points[b].tolist(),'interior_existing_vertices':[points[i].tolist() for i in sequence[1:-1]],
                    'maximum_collinearity_residual_m':float(distance[interior].max())})
            for i,j in zip(sequence,sequence[1:]):
                key=tuple(sorted((i,j)))
                refined[key]+=1
                winding[key]+=1 if i<j else -1
    return {'raw_non_two_incident_edges':sum(n!=2 for n in original.values()),
        'subdivided_non_two_incident_segments':sum(n!=2 for n in refined.values()),
        'subdivided_inconsistent_winding':sum(refined[k]==2 and value!=0 for k,value in winding.items()),
        'subdivisions':splits,'collinearity_tolerance_m':tolerance,
        'scope':'Existing-vertex edge bookkeeping only; no geometry moved or face capped.'}


def nearest_surface(point,vertices,faces):
    point=np.asarray(point,float)
    triangles=np.asarray(vertices,float)[np.asarray(faces,int)]
    a=triangles[:,0]
    e1=triangles[:,1]-a
    e2=triangles[:,2]-a
    normals=np.cross(e1,e2)
    norm2=np.einsum('ij,ij->i',normals,normals)
    displacement=point-a
    numerator=np.einsum('ij,ij->i',displacement,normals)
    fraction=np.divide(numerator,norm2,out=np.zeros_like(norm2),where=norm2>1e-24)
    projection=point-fraction[:,None]*normals
    delta=projection-a
    d00=np.einsum('ij,ij->i',e1,e1)
    d01=np.einsum('ij,ij->i',e1,e2)
    d11=np.einsum('ij,ij->i',e2,e2)
    denominator=d00*d11-d01*d01
    d20=np.einsum('ij,ij->i',delta,e1)
    d21=np.einsum('ij,ij->i',delta,e2)
    u=np.divide(d11*d20-d01*d21,denominator,out=np.zeros_like(norm2),where=denominator>1e-24)
    v=np.divide(d00*d21-d01*d20,denominator,out=np.zeros_like(norm2),where=denominator>1e-24)
    interior=(denominator>1e-24)&(u>=0)&(v>=0)&(u+v<=1)
    candidates=[np.where(interior[:,None],projection,np.full_like(projection,np.inf))]
    for first,second in ((0,1),(1,2),(2,0)):
        begin=triangles[:,first]
        vector=triangles[:,second]-begin
        length2=np.einsum('ij,ij->i',vector,vector)
        t=np.divide(np.einsum('ij,ij->i',point-begin,vector),length2,out=np.zeros_like(length2),where=length2>0)
        candidates.append(begin+np.clip(t,0,1)[:,None]*vector)
    positions=np.stack(candidates)
    distances=np.linalg.norm(positions-point,axis=2)
    kind,index=np.unravel_index(np.argmin(distances),distances.shape)
    normal=normals[index]/np.sqrt(norm2[index]) if norm2[index]>0 else None
    return {'distance_m':float(distances[kind,index]),'closest_point_m':positions[kind,index].tolist(),
        'triangle_index':int(index),'triangle_vertices_m':triangles[index].tolist(),
        'face_normal':normal.tolist() if normal is not None else None}
