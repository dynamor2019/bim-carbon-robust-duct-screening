"""Planarity and simple-polygon ear clipping audit; no invalid face repair."""
import numpy as np


def cross2(a,b):
    return float(a[0]*b[1]-a[1]*b[0])


def face_analysis(points,planarity_tolerance=1e-6):
    points=np.asarray(points,float)
    if len(points)<3 or not np.isfinite(points).all():
        return {'status':'INVALID_INPUT','triangles':[]}
    origin=points.mean(axis=0)
    _,_,axes=np.linalg.svd(points-origin,full_matrices=False)
    normal=axes[-1]
    residual=float(np.abs((points-origin)@normal).max())
    xy=np.column_stack([(points-origin)@axes[0],(points-origin)@axes[1]])
    area=sum(cross2(a,b) for a,b in zip(xy,np.roll(xy,-1,axis=0)))/2
    intersections=[]
    details=[]
    def on(a,b,p):
        return abs(cross2(b-a,p-a))<=1e-12 and np.all(p>=np.minimum(a,b)-1e-10) and np.all(p<=np.maximum(a,b)+1e-10)
    for i in range(len(xy)):
        a,b=xy[i],xy[(i+1)%len(xy)]
        for j in range(i+1,len(xy)):
            if j==(i+1)%len(xy) or i==(j+1)%len(xy):
                continue
            c,d=xy[j],xy[(j+1)%len(xy)]
            o1,o2=cross2(b-a,c-a),cross2(b-a,d-a)
            o3,o4=cross2(d-c,a-c),cross2(d-c,b-c)
            proper=((o1>1e-12 and o2<-1e-12) or (o1<-1e-12 and o2>1e-12)) and ((o3>1e-12 and o4<-1e-12) or (o3<-1e-12 and o4>1e-12))
            if proper or on(a,b,c) or on(a,b,d) or on(c,d,a) or on(c,d,b):
                intersections.append([i,j])
                details.append({'edge_indices':[i,j],'kind':'PROPER_CROSSING' if proper else 'NONADJACENT_CONTACT_OR_COLLINEAR_OVERLAP',
                    'edge_endpoints_m':[points[[i,(i+1)%len(points)]].tolist(),points[[j,(j+1)%len(points)]].tolist()]})
    degenerate=int(sum(np.linalg.norm(b-a)<=1e-10 for a,b in zip(xy,np.roll(xy,-1,axis=0))))
    result={'status':'PENDING','vertex_count':len(points),'plane_residual_m':residual,
        'projected_signed_area_m2':float(area),'nonadjacent_intersections':intersections,'intersection_details':details,
        'zero_length_edges':degenerate,'triangles':[],'planarity_tolerance_m':planarity_tolerance}
    if residual>planarity_tolerance or intersections or degenerate or abs(area)<=1e-12:
        result['status']='INVALID_FOR_PLANAR_TRIANGULATION'
        return result
    sign=1 if area>0 else -1
    remaining=list(range(len(points)))
    triangles=[]
    while len(remaining)>3:
        found=False
        for k,index in enumerate(remaining):
            previous,following=remaining[k-1],remaining[(k+1)%len(remaining)]
            a,b,c=xy[[previous,index,following]]
            if sign*cross2(b-a,c-b)<=1e-12:
                continue
            inside=False
            for other in remaining:
                if other in (previous,index,following):
                    continue
                p=xy[other]
                if min(sign*cross2(b-a,p-a),sign*cross2(c-b,p-b),sign*cross2(a-c,p-c))>=-1e-12:
                    inside=True
                    break
            if inside:
                continue
            triangles.append([previous,index,following])
            remaining.pop(k)
            found=True
            break
        if not found:
            result['status']='EAR_CLIPPING_UNRESOLVED'
            return result
    triangles.append(remaining)
    tri_area=sum(abs(cross2(xy[b]-xy[a],xy[c]-xy[a]))/2 for a,b,c in triangles)
    result.update({'status':'PLANAR_SIMPLE_TRIANGULATED','triangles':triangles,
        'triangulated_area_m2':float(tri_area),'area_residual_m2':float(tri_area-abs(area))})
    return result
