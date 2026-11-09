"""Exact series/parallel reduction of positive fixed-quadratic tree resistances.
All leaf boundaries have one common pressure, no controls or signed tee coupling.
R units Pa/(m3/s)^2. Resistance provenance/applicability remains upstream.
"""
import math
from candidate_tree_flow import validate_tree


def positive(x,zero=False):
    return type(x) in (int,float) and math.isfinite(x) and (x>=0 if zero else x>0)


def solve(nodes,edges,root,terminal_resistances,edge_resistances,total_flow_m3_s,model):
    if not positive(total_flow_m3_s,True) or not isinstance(model,dict):
        raise ValueError('Finite nonnegative prescribed total flow and model declaration required')
    if model.get('boundary')!='COMMON_LEAF_PRESSURE' or model.get('resistance_law')!='FIXED_QUADRATIC' or model.get('controls')!='NONE':
        raise ValueError('Only common leaf pressure fixed quadratic passive tree is supported')
    if not isinstance(model.get('source_ref'),str) or not model['source_ref'].strip():
        raise ValueError('Model/source applicability reference required')
    if not isinstance(terminal_resistances,dict) or not terminal_resistances or not all(positive(r) for r in terminal_resistances.values()):
        raise ValueError('Positive terminal resistances required; singular free terminals unsupported')
    if not isinstance(edge_resistances,dict) or set(edge_resistances)!={e['id'] for e in edges} or not all(positive(r,True) for r in edge_resistances.values()):
        raise ValueError('Explicit finite nonnegative resistance for every edge required')
    # Validate structure/authorization declarations; zero bookkeeping demands do not
    # impose a target allocation and velocity feasibility is not used as a certificate.
    validate_tree(nodes,edges,root,{n:0. for n in terminal_resistances},1.)
    parent={e['from']:e for e in edges}
    children={n:[] for n in nodes}
    for e in edges:
        children[e['to']].append(e['from'])
    equivalents={}
    active=set()
    def reduce_node(n):
        if n in equivalents:
            return equivalents[n]
        if n in active:
            raise ValueError('Cyclic network')
        active.add(n)
        if n in terminal_resistances:
            value=terminal_resistances[n]
        else:
            conductance=sum(1/math.sqrt(edge_resistances[parent[c]['id']]+reduce_node(c)) for c in children[n])
            if not positive(conductance):
                raise ValueError('Invalid parallel conductance')
            value=1/conductance**2
        if not positive(value):
            raise ValueError('Invalid/nonfinite equivalent resistance')
        equivalents[n]=value
        active.remove(n)
        return value
    equivalent=reduce_node(root)
    pressure=equivalent*total_flow_m3_s**2
    if not math.isfinite(pressure):
        raise ValueError('Nonfinite root pressure')
    node_flow={root:total_flow_m3_s}
    edge_flow={}
    terminal_flow={}
    def distribute(n,q):
        if n in terminal_resistances:
            terminal_flow[n]=q
            return
        weights={c:1/math.sqrt(edge_resistances[parent[c]['id']]+equivalents[c]) for c in children[n]}
        denominator=sum(weights.values())
        for c in sorted(children[n]):
            flow=q*weights[c]/denominator
            node_flow[c]=flow
            edge_flow[parent[c]['id']]=flow
            distribute(c,flow)
    distribute(root,total_flow_m3_s)
    paths=[]
    for terminal,flow in sorted(terminal_flow.items()):
        loss=terminal_resistances[terminal]*flow**2
        current=terminal
        route=[]
        while current!=root:
            edge=parent[current]
            loss+=edge_resistances[edge['id']]*edge_flow[edge['id']]**2
            route.append(edge['id'])
            current=edge['to']
        paths.append({'terminal':terminal,'flow_m3_s':flow,'path':route,'path_pressure_Pa':loss,'root_pressure_residual_Pa':loss-pressure})
    flow_residual=sum(terminal_flow.values())-total_flow_m3_s
    if abs(flow_residual)>max(1e-12,total_flow_m3_s*1e-12) or any(abs(p['root_pressure_residual_Pa'])>max(1e-9,abs(pressure)*1e-10) for p in paths):
        raise ValueError('Flow/pressure residual gate failed')
    return {'status':'PASS_FIXED_QUADRATIC_COMMON_BOUNDARY_MODEL_ONLY','total_flow_m3_s':total_flow_m3_s,
        'equivalent_resistance_Pa_per_m3_s_squared':equivalent,'system_pressure_Pa':pressure,'edge_flow_m3_s':edge_flow,
        'terminal_flow_m3_s':terminal_flow,'paths':paths,'total_flow_residual_m3_s':flow_residual,
        'model':model,'actual_service_certified':False,'design_demands_satisfied':None,
        'scope':'PASSIVE_POSITIVE_QUADRATIC_TREE_WITH_COMMON_LEAF_PRESSURE_ONLY'}


def system_points(equivalent_resistance,flows):
    if not positive(equivalent_resistance) or not isinstance(flows,list) or len(flows)<2 or not all(positive(q,True) for q in flows) or any(b<=a for a,b in zip(flows,flows[1:])):
        raise ValueError('Positive resistance and increasing nonnegative explicit flow grid required')
    result=[{'flow_m3_s':q,'pressure_Pa':equivalent_resistance*q**2} for q in flows]
    if not all(math.isfinite(p['pressure_Pa']) for p in result):
        raise ValueError('Nonfinite system curve')
    return result
