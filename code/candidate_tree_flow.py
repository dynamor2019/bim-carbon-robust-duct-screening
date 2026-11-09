"""Validate explicitly authorized exhaust-tree candidates. No IFC contact inference.

Edges point terminal/branch -> root. Inputs are SI. Authorization is supplied by
an upstream evidence gate; booleans here do not independently certify geometry.
"""
import math


def positive(value,zero=False):
    return not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value) and (value>=0 if zero else value>0)


def validate_tree(nodes,edges,root,terminal_demands,maximum_velocity):
    if not isinstance(nodes,(list,tuple)) or not nodes or not all(isinstance(n,str) and n.strip() for n in nodes) or len(set(nodes))!=len(nodes):
        raise ValueError('Unique nonempty node IDs required')
    if root not in nodes or not isinstance(edges,list) or not positive(maximum_velocity):
        raise ValueError('Declared root, edge list and positive velocity limit required')
    if not isinstance(terminal_demands,dict) or not terminal_demands or root in terminal_demands:
        raise ValueError('Nonempty terminal demands required; root cannot be a terminal')
    if not set(terminal_demands)<=set(nodes) or not all(positive(q,zero=True) for q in terminal_demands.values()):
        raise ValueError('Declared terminals require finite nonnegative m3/s demands')
    parent={}
    incoming={n:[] for n in nodes}
    ids=set()
    for edge in edges:
        if not isinstance(edge,dict):
            raise ValueError('Typed edge records required')
        eid=edge.get('id')
        a,b=edge.get('from'),edge.get('to')
        if not isinstance(eid,str) or not eid.strip() or eid in ids or a not in nodes or b not in nodes or a==b:
            raise ValueError('Unique edge IDs and distinct declared endpoints required')
        if a==root or a in parent:
            raise ValueError('Every nonroot node needs exactly one outgoing edge toward root')
        if not positive(edge.get('length_m')) or not positive(edge.get('diameter_m')):
            raise ValueError('Finite positive source/candidate length and diameter required')
        if edge.get('spatial_authorized') is not True or edge.get('connection_authorized') is not True:
            raise ValueError('Uncertified spatial domain or service connection; numerical contact is insufficient')
        if not isinstance(edge.get('authorization_ref'),str) or not edge['authorization_ref'].strip():
            raise ValueError('Upstream evidence authorization reference required')
        parent[a]=edge
        incoming[b].append(a)
        ids.add(eid)
    if set(parent)!=set(nodes)-{root}:
        raise ValueError('Disconnected node or missing route edge')
    paths={}
    for start in sorted(nodes):
        current=start
        seen=set()
        route=[]
        while current!=root:
            if current in seen:
                raise ValueError('Cycle detected; no route to root')
            seen.add(current)
            edge=parent[current]
            route.append(edge['id'])
            current=edge['to']
        paths[start]=route
    leaves={n for n in nodes if not incoming[n] and n!=root}
    if leaves!=set(terminal_demands):
        raise ValueError('All leaves must have explicit terminal demand, and terminals must be leaves')
    node_flow={n:0. for n in nodes}
    edge_flow={edge['id']:0. for edge in edges}
    for terminal,q in terminal_demands.items():
        node_flow[terminal]+=q
        current=terminal
        while current!=root:
            edge=parent[current]
            edge_flow[edge['id']]+=q
            current=edge['to']
            node_flow[current]+=q
    rows=[]
    for edge in sorted(edges,key=lambda e:e['id']):
        q=edge_flow[edge['id']]
        area=math.pi*edge['diameter_m']**2/4
        velocity=q/area
        if not math.isfinite(area) or area<=0 or not math.isfinite(velocity):
            raise ValueError('Cross-section calculation overflow/underflow')
        rows.append({'edge_id':edge['id'],'flow_m3_s':q,'area_m2':area,'velocity_m_s':velocity,
            'velocity_feasible':velocity<=maximum_velocity,'length_m':edge['length_m'],'diameter_m':edge['diameter_m'],
            'authorization_ref':edge['authorization_ref']})
    conservation=[]
    for n in sorted(nodes):
        inflow=sum(edge_flow[parent[c]['id']] for c in incoming[n])+terminal_demands.get(n,0.)
        outflow=edge_flow[parent[n]['id']] if n!=root else node_flow[root]
        residual=inflow-outflow
        conservation.append({'node':n,'inflow_plus_terminal_m3_s':inflow,'outflow_or_root_total_m3_s':outflow,
            'residual_m3_s':residual})
    total=sum(terminal_demands.values())
    if not math.isfinite(total) or any(not math.isfinite(r['residual_m3_s']) or abs(r['residual_m3_s'])>max(1e-12,total*1e-12) for r in conservation):
        raise ValueError('Flow conservation or finite arithmetic check failed')
    return {'status':'PASS_TREE_FLOW_AND_VELOCITY_ONLY' if all(r['velocity_feasible'] for r in rows) else 'FAIL_VELOCITY_LIMIT',
        'root':root,'terminal_total_m3_s':total,'edges':rows,'node_conservation':conservation,
        'terminal_paths':{n:paths[n] for n in sorted(terminal_demands)},
        'pressure_balance_checked':False,'fan_capacity_checked':False,'installation_independently_certified':False,
        'scope':'SUPPLIED_AUTHORIZED_DIRECTED_TREE_ONLY_NOT_REAL_IFC_TOPOLOGY_CERTIFICATION'}
