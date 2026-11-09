"""Bind supplied edge authorization to current local evidence; no certification inference.

This validates declared evidence structure/provenance only. Whether a reviewed
report establishes engineering validity still requires independent review.
"""
import json
import math
from pathlib import Path
from guard_engineering_inputs import local_evidence,sha

ROLES={'geometry':'CANDIDATE_EDGE_GEOMETRY','spatial':'ROUTING_ENVELOPE_AND_CLEARANCE',
       'service':'PHYSICAL_CONNECTION_AND_SERVICE'}


def edge_fingerprint(edge):
    import hashlib
    fields=('id','from','to','length_m','diameter_m','polyline_m','source_mapping')
    if any(k not in edge for k in fields):
        raise ValueError('Complete edge geometry/source mapping required')
    # Reject nonfinite JSON; no rounded coordinates or geometry repair.
    text=json.dumps({k:edge[k] for k in fields},sort_keys=True,separators=(',',':'),allow_nan=False)
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def authorize(edge,bundle,project):
    project=Path(project).resolve()
    try:
        fingerprint=edge_fingerprint(edge)
    except (ValueError,TypeError):
        return {'status':'BLOCKED_EDGE_EVIDENCE','checks':[{'name':'edge_fingerprint','status':'FAIL','evidence':'Missing/nonfinite edge geometry or mapping.'}],
                'authorized_edge':None}
    checks=[]
    def add(name,ok,evidence):
        checks.append({'name':name,'status':'PASS' if ok else 'FAIL','evidence':evidence})
    points=edge.get('polyline_m')
    valid_points=isinstance(points,list) and len(points)>=2 and all(isinstance(p,list) and len(p)==3 and all(type(x) in (int,float) and math.isfinite(x) for x in p) for p in points)
    length=edge.get('length_m')
    diameter=edge.get('diameter_m')
    valid_numbers=type(length) in (int,float) and math.isfinite(length) and length>0 and type(diameter) in (int,float) and math.isfinite(diameter) and diameter>0
    derived_length=None
    if valid_points:
        derived_length=sum(math.dist(a,b) for a,b in zip(points,points[1:]))
    add('geometry_si',valid_points and valid_numbers and derived_length is not None and math.isfinite(derived_length) and abs(derived_length-length)<=max(1e-9,length*1e-9),
        'Metre polyline length must agree with edge length; tolerance is arithmetic consistency only.')
    mapping=edge.get('source_mapping')
    add('source_mapping',isinstance(mapping,dict) and bool(mapping),'Explicit mapping/candidate provenance required; not inferred from contact.')
    bundle=bundle if isinstance(bundle,dict) else {}
    add('bundle_edge_binding',bundle.get('edge_id')==edge.get('id') and bundle.get('edge_sha256')==fingerprint,'Authorization bundle must bind exact current edge geometry/source mapping.')
    refs=bundle.get('reports',{})
    paths=[]
    for role,scope in ROLES.items():
        record=refs.get(role) if isinstance(refs,dict) else None
        ok=local_evidence(record,project)
        explanation='Missing/stale/outside-project evidence record.'
        if ok:
            path=(project/record['path']).resolve()
            paths.append(str(path))
            try:
                data=json.loads(path.read_text(encoding='utf-8'))
                items=data.get('checks')
                sources=data.get('sourceHashes')
                ok=(data.get('scope')==scope and data.get('status')=='PASS' and data.get('edge_id')==edge.get('id')
                    and data.get('edgeSha256')==fingerprint and data.get('unit')=='m'
                    and isinstance(items,list) and bool(items) and all(isinstance(c,dict) and c.get('status')=='PASS' and c.get('name') and c.get('evidence') for c in items)
                    and isinstance(sources,dict) and bool(sources)
                    and isinstance(data.get('method'),str) and bool(data['method'].strip()))
                if isinstance(sources,dict):
                    ok=ok and all(local_evidence({'path':relative,'sha256':digest},project) for relative,digest in sources.items())
                if role=='spatial':
                    clearance=data.get('clearance_m')
                    ok=ok and type(clearance) in (int,float) and math.isfinite(clearance) and clearance>=0 and data.get('envelopeDiameter_m')==diameter
                if role=='service':
                    ok=ok and data.get('from')==edge.get('from') and data.get('to')==edge.get('to') and data.get('direction_certified') is True
                    ok=ok and isinstance(data.get('service_id'),str) and bool(data['service_id'].strip())
                explanation='Role-specific current source hashes, edge hash, SI scope and nonempty scientific checks required; semantic truth is reviewed separately.'
            except (ValueError,TypeError,AttributeError):
                ok=False
                explanation='Malformed evidence report.'
        add(role+'_evidence',ok,explanation)
    add('distinct_reports',len(paths)==3 and len(set(paths))==3,'Geometry, spatial and service roles cannot reuse one report path.')
    passed=all(c['status']=='PASS' for c in checks)
    authorized=None
    if passed:
        import hashlib
        bundle_hash=hashlib.sha256(json.dumps(bundle,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()
        authorized=dict(edge,spatial_authorized=True,connection_authorized=True,
            authorization_ref='EDGE_EVIDENCE_BUNDLE_SHA256:'+bundle_hash)
    return {'status':'PASS_EVIDENCE_BINDINGS_ONLY' if passed else 'BLOCKED_EDGE_EVIDENCE',
        'edge_sha256':fingerprint,'checks':checks,'authorized_edge':authorized,
        'independent_engineering_certification':False}
