"""Audit original indexed polygon loops without triangulating or capping them."""
from collections import Counter,defaultdict


def polygon_boundary_incidence(loops):
    counts=Counter()
    winding=defaultdict(int)
    degenerate=0
    for loop in loops:
        if len(loop)<3 or len(set(loop))<3:
            degenerate+=1
        for a,b in zip(loop,loop[1:]+loop[:1]):
            a,b=int(a),int(b)
            key=tuple(sorted((a,b)))
            counts[key]+=1
            winding[key]+=1 if a<b else -1
    return {'loop_count':len(loops),'degenerate_loops':degenerate,
        'non_two_incident_edges':sum(n!=2 for n in counts.values()),
        'inconsistent_edge_winding':sum(counts[k]==2 and v!=0 for k,v in winding.items()),
        'unpaired_edges':[{'coordinate_indices':list(k),'incidence':n,'winding_sum':winding[k]} for k,n in sorted(counts.items()) if n!=2],
        'scope':'Direct native coordinate-index edge incidence; no geometric welding or closure repair.'}
