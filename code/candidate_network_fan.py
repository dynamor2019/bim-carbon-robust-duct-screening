"""Fixed quadratic passive-tree / tabulated fan co-evaluation, not real case certification."""
import math
from candidate_quadratic_balance import solve
from candidate_fan_curve import screen_curve
from candidate_operating_point import validate_curve


def direct_roots(points,resistance,stable_interval,flow_tolerance,pressure_tolerance):
    validate_curve(points)
    if type(resistance) not in (int,float) or not math.isfinite(resistance) or resistance<=0:
        raise ValueError('Positive finite quadratic system resistance required')
    if not isinstance(stable_interval,list) or len(stable_interval)!=2 or not all(type(x) in (int,float) and math.isfinite(x) and x>=0 for x in stable_interval) or stable_interval[0]>=stable_interval[1]:
        raise ValueError('Declared stable interval required')
    if stable_interval[0]<points[0]['flow_m3_s'] or stable_interval[1]>points[-1]['flow_m3_s']:
        raise ValueError('Stable interval outside curve support')
    if not all(type(x) in (int,float) and math.isfinite(x) and x>0 for x in (flow_tolerance,pressure_tolerance)):
        raise ValueError('Explicit positive numerical tolerances required')
    roots=[]
    for i,(a,b) in enumerate(zip(points,points[1:])):
        slope=(b['pressure_Pa']-a['pressure_Pa'])/(b['flow_m3_s']-a['flow_m3_s'])
        intercept=a['pressure_Pa']-slope*a['flow_m3_s']
        # R Q^2 - slope Q - intercept=0; retain every real supported root.
        discriminant=slope*slope+4*resistance*intercept
        if not all(math.isfinite(x) for x in (slope,intercept,discriminant)):
            raise ValueError('Nonfinite quadratic coefficients; no clipped repair')
        if discriminant<0:
            continue
        sqrt_d=math.sqrt(discriminant)
        # Stable quadratic formula avoids cancellation on the small root.
        qterm=.5*(slope+math.copysign(sqrt_d,slope))
        candidates=[qterm/resistance]
        if qterm!=0:
            candidates.append(-intercept/qterm)
        elif discriminant==0:
            candidates=[slope/(2*resistance)]
        low=max(a['flow_m3_s'],stable_interval[0])
        high=min(b['flow_m3_s'],stable_interval[1])
        for q in candidates:
            if not math.isfinite(q) or q<=0 or not low<=q<=high:
                continue
            residual=slope*q+intercept-resistance*q*q
            if abs(residual)>pressure_tolerance:
                raise ValueError('Analytical root residual exceeds declared numerical tolerance')
            roots.append({'flow_m3_s':q,'pressure_Pa':resistance*q*q,'residual_Pa':residual,
                'segment_index':i,'net_pressure_slope_Pa_per_m3_s':slope-2*resistance*q})
    roots.sort(key=lambda r:(r['flow_m3_s'],r['segment_index']))
    grouped=[]
    for row in roots:
        if grouped and abs(row['flow_m3_s']-grouped[-1]['flow_m3_s'])<=flow_tolerance:
            grouped[-1]['segment_records'].append(row)
        else:
            grouped.append({'flow_m3_s':row['flow_m3_s'],'pressure_Pa':row['pressure_Pa'],'segment_records':[row]})
    for row in grouped:
        row['negative_net_slope_all_segments']=all(s['net_pressure_slope_Pa_per_m3_s']<0 for s in row['segment_records'])
    return grouped


def evaluate(nodes,edges,root,terminal_resistances,edge_resistances,model,fan,conditions,pressure_basis,demand_bounds,flow_tolerance,pressure_tolerance):
    if not isinstance(demand_bounds,dict) or set(demand_bounds)!=set(terminal_resistances):
        raise ValueError('Explicit demand bounds for every terminal required')
    for bounds in demand_bounds.values():
        if not isinstance(bounds,dict) or not all(type(bounds.get(k)) in (int,float) and math.isfinite(bounds[k]) and bounds[k]>=0 for k in ('minimum_m3_s','maximum_m3_s')) or bounds['minimum_m3_s']>bounds['maximum_m3_s']:
            raise ValueError('Nonnegative ordered explicit terminal demand bounds required')
        if not isinstance(bounds.get('source_ref'),str) or not bounds['source_ref'].strip():
            raise ValueError('Design demand/tolerance provenance required; no default flow acceptance')
    baseline=solve(nodes,edges,root,terminal_resistances,edge_resistances,1.,model)
    resistance=baseline['equivalent_resistance_Pa_per_m3_s_squared']
    # Validate fan conditions/power basis/stable interval independently even if no root.
    interval=fan.get('stable_flow_interval_m3_s')
    if not isinstance(interval,list) or len(interval)!=2:
        raise ValueError('Fan stable interval required')
    midpoint=(interval[0]+interval[1])/2
    screen_curve(fan,midpoint,0.,pressure_basis,conditions)
    roots=direct_roots(fan['points'],resistance,interval,flow_tolerance,pressure_tolerance)
    evaluated=[]
    for intersection in roots:
        q=intersection['flow_m3_s']
        network=solve(nodes,edges,root,terminal_resistances,edge_resistances,q,model)
        curve=screen_curve(fan,q,0.,pressure_basis,conditions)
        terminal_rows=[]
        for terminal,flow in sorted(network['terminal_flow_m3_s'].items()):
            bounds=demand_bounds[terminal]
            status='UNDERSUPPLY' if flow<bounds['minimum_m3_s'] else ('OVERSUPPLY' if flow>bounds['maximum_m3_s'] else 'WITHIN_DECLARED_BOUNDS')
            terminal_rows.append({'terminal':terminal,'flow_m3_s':flow,'bounds':bounds,'status':status})
        evaluated.append({'intersection':intersection,'network':network,'fan_curve':curve,'terminal_checks':terminal_rows,
            'all_terminal_bounds_satisfied':all(r['status']=='WITHIN_DECLARED_BOUNDS' for r in terminal_rows)})
    status='NO_SUPPORTED_INTERSECTION' if not evaluated else ('AMBIGUOUS_MULTIPLE_INTERSECTIONS' if len(evaluated)>1 else ('PASS_RESTRICTED_MODEL_DEMAND_CHECK_ONLY' if evaluated[0]['all_terminal_bounds_satisfied'] and evaluated[0]['intersection']['negative_net_slope_all_segments'] else 'FAIL_RESTRICTED_MODEL_DEMAND_OR_SLOPE'))
    return {'status':status,'operating_candidates':evaluated,'equivalent_resistance':resistance,
        'actual_operation_certified':False,'complete_engineering_feasibility':None,
        'scope':'FIXED_QUADRATIC_COMMON_BOUNDARY_PASSIVE_TREE_AND_PIECEWISE_LINEAR_FAN_ONLY'}
