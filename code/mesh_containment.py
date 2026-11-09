"""Numerical closed-triangle-mesh screening, not physical room/service certification."""
from collections import Counter,defaultdict
import numpy as np

DIRECTIONS=np.array([[1,.371,.529],[.283,1,.617],[.419,.227,1.]])


def mesh_integrity(vertices,faces):
    vertices=np.asarray(vertices,dtype=float)
    faces=np.asarray(faces,dtype=int)
    if vertices.ndim!=2 or vertices.shape[1]!=3 or faces.ndim!=2 or faces.shape[1]!=3 or not len(faces):
        raise ValueError('Nontriangular or empty mesh')
    if not np.isfinite(vertices).all() or faces.min()<0 or faces.max()>=len(vertices):
        raise ValueError('Nonfinite vertices or invalid face indices')
    _,weld=np.unique(np.round(vertices,8),axis=0,return_inverse=True)
    edges=Counter()
    winding=defaultdict(int)
    degenerate=0
    for original,triangle in zip(faces,weld[faces]):
        a,b,c=vertices[original]
        if len(set(triangle))<3 or np.linalg.norm(np.cross(b-a,c-a))<=1e-12:
            degenerate+=1
        for i,j in zip(triangle,np.roll(triangle,-1)):
            key=tuple(sorted((int(i),int(j))))
            edges[key]+=1
            winding[key]+=1 if i<j else -1
    bad=sum(n!=2 for n in edges.values())
    inconsistent=sum(edges[key]==2 and value!=0 for key,value in winding.items())
    triangles=vertices[faces]
    reference=vertices.mean(axis=0)
    shifted=triangles-reference
    volume=float(np.einsum('ij,ij->i',shifted[:,0],np.cross(shifted[:,1],shifted[:,2])).sum()/6)
    valid=not bad and not degenerate and not inconsistent and abs(volume)>1e-10
    return {'status':'EDGE_CLOSED_ORIENTED' if valid else 'INVALID_FOR_PARITY_SCREEN',
        'vertices':len(vertices),'triangles':len(faces),'non_two_incident_edges':bad,
        'inconsistent_edge_winding':inconsistent,'degenerate_triangles':degenerate,
        'signed_volume_m3':volume,'coordinate_weld_decimal_places':8,
        'self_intersection_and_vertex_link_check':'NOT_PERFORMED'}


def classify_point(point,vertices,faces,integrity=None,tolerance=1e-6):
    vertices=np.asarray(vertices,dtype=float)
    triangles=vertices[np.asarray(faces,dtype=int)]
    point=np.asarray(point,dtype=float)
    integrity=integrity or mesh_integrity(vertices,faces)
    if integrity['status']!='EDGE_CLOSED_ORIENTED':
        return {'status':'INVALID_MESH','rays':[]}
    a=triangles[:,0]
    e1=triangles[:,1]-a
    e2=triangles[:,2]-a
    normals=np.cross(e1,e2)
    norm2=np.einsum('ij,ij->i',normals,normals)
    displacement=point-a
    height=np.einsum('ij,ij->i',displacement,normals)
    projection=displacement-(height/norm2)[:,None]*normals
    d00=np.einsum('ij,ij->i',e1,e1)
    d01=np.einsum('ij,ij->i',e1,e2)
    d11=np.einsum('ij,ij->i',e2,e2)
    d20=np.einsum('ij,ij->i',projection,e1)
    d21=np.einsum('ij,ij->i',projection,e2)
    denominator=d00*d11-d01*d01
    u=(d11*d20-d01*d21)/denominator
    v=(d00*d21-d01*d20)/denominator
    boundary=(np.abs(height)/np.sqrt(norm2)<=tolerance)&(u>=-1e-10)&(v>=-1e-10)&(u+v<=1+1e-10)
    if boundary.any():
        return {'status':'BOUNDARY','rays':[],'tolerance_m':tolerance}
    rays=[]
    for direction in DIRECTIONS:
        direction=direction/np.linalg.norm(direction)
        cross=np.cross(np.broadcast_to(direction,e2.shape),e2)
        determinant=np.einsum('ij,ij->i',e1,cross)
        valid=np.abs(determinant)>1e-12
        inverse=np.divide(1.,determinant,out=np.zeros_like(determinant),where=valid)
        u=inverse*np.einsum('ij,ij->i',displacement,cross)
        q=np.cross(displacement,e1)
        v=inverse*np.einsum('j,ij->i',direction,q)
        distance=inverse*np.einsum('ij,ij->i',e2,q)
        selected=valid&(u>=-1e-10)&(v>=-1e-10)&(u+v<=1+1e-10)&(distance>tolerance)
        hits=np.sort(distance[selected])
        events=[]
        for value in hits:
            if not events or value-events[-1]>tolerance:
                events.append(float(value))
        rays.append({'direction':direction.tolist(),'intersection_events':len(events),'odd':bool(len(events)%2)})
    parity=[r['odd'] for r in rays]
    return {'status':'INSIDE_NUMERICAL' if all(parity) else 'OUTSIDE_NUMERICAL' if not any(parity) else 'RAY_DISAGREEMENT',
        'rays':rays,'tolerance_m':tolerance}
