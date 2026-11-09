"""Validate planar polygon holes without filling, joining or reordering rings."""
import numpy as np
from polygon_geometry import face_analysis,cross2


def point_in_ring(point,ring,tolerance=1e-8):
    point=np.asarray(point,float)
    ring=np.asarray(ring,float)
    inside=False
    for a,b in zip(ring,np.roll(ring,-1,axis=0)):
        vector=b-a
        length2=float(vector@vector)
        fraction=np.clip(float((point-a)@vector)/length2,0,1) if length2>0 else 0
        if np.linalg.norm(point-(a+fraction*vector))<=tolerance:
            return 'BOUNDARY'
        if (a[1]>point[1])!=(b[1]>point[1]):
            x=a[0]+(point[1]-a[1])*(b[0]-a[0])/(b[1]-a[1])
            if point[0]<x:
                inside=not inside
    return 'INSIDE' if inside else 'OUTSIDE'


def ring_contacts(first,second,tolerance=1e-8):
    contacts=[]
    def on(a,b,p):
        v=b-a
        length2=float(v@v)
        t=float((p-a)@v)/length2 if length2 else 0
        return 0<=t<=1 and np.linalg.norm(p-(a+t*v))<=tolerance
    for i,(a,b) in enumerate(zip(first,np.roll(first,-1,axis=0))):
        for j,(c,d) in enumerate(zip(second,np.roll(second,-1,axis=0))):
            o1,o2=cross2(b-a,c-a),cross2(b-a,d-a)
            o3,o4=cross2(d-c,a-c),cross2(d-c,b-c)
            proper=((o1>1e-12 and o2<-1e-12) or (o1<-1e-12 and o2>1e-12)) and ((o3>1e-12 and o4<-1e-12) or (o3<-1e-12 and o4>1e-12))
            if proper or on(a,b,c) or on(a,b,d) or on(c,d,a) or on(c,d,b):
                contacts.append({'edges':[i,j],'kind':'CROSSING' if proper else 'CONTACT'})
    return contacts


def hole_audit(outer,holes):
    outer=np.asarray(outer,float)
    holes=[np.asarray(h,float) for h in holes]
    audits=[face_analysis(ring) for ring in [outer]+holes]
    if any(a['status']!='PLANAR_SIMPLE_TRIANGULATED' for a in audits):
        return {'status':'INVALID_RING_GEOMETRY','ring_audits':audits}
    origin=outer.mean(axis=0)
    _,_,axes=np.linalg.svd(outer-origin,full_matrices=False)
    xy=[np.column_stack([(r-origin)@axes[0],(r-origin)@axes[1]]) for r in [outer]+holes]
    residual=max(float(np.abs((ring-origin)@axes[-1]).max()) for ring in [outer]+holes)
    issues=[]
    if residual>1e-6:
        issues.append({'kind':'NONCOPLANAR_RINGS','residual_m':residual})
    for i,hole in enumerate(xy[1:]):
        statuses=[point_in_ring(p,xy[0]) for p in hole]
        if any(status!='INSIDE' for status in statuses):
            issues.append({'kind':'HOLE_NOT_STRICTLY_INSIDE_OUTER','hole':i,'vertex_statuses':statuses})
        contacts=ring_contacts(xy[0],hole)
        if contacts:
            issues.append({'kind':'HOLE_OUTER_CONTACT','hole':i,'contacts':contacts})
        for j,other in enumerate(xy[1:i+1]):
            contacts=ring_contacts(hole,other)
            nested=point_in_ring(hole[0],other)!='OUTSIDE' or point_in_ring(other[0],hole)!='OUTSIDE'
            if contacts or nested:
                issues.append({'kind':'HOLE_HOLE_CONTACT_OR_NESTING','holes':[j,i],'contacts':contacts,'nested':nested})
    areas=[abs(a['projected_signed_area_m2']) for a in audits]
    net=areas[0]-sum(areas[1:])
    if net<=0:
        issues.append({'kind':'NONPOSITIVE_NET_AREA'})
    return {'status':'PASS_HOLE_RING_SCOPE' if not issues else 'INVALID_HOLE_DOMAIN',
        'hole_count':len(holes),'plane_residual_m':residual,'outer_area_m2':areas[0],
        'hole_areas_m2':areas[1:],'net_area_m2':net,'issues':issues,'ring_audits':audits,
        'limitations':['No hole bridging or triangulation; orientation is recorded in ring audits but not silently normalized.']}
