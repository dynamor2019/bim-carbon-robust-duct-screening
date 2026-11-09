"""Interpolate an explicit fixed-speed curve at prescribed demand; no equilibrium solver.
Electrical power must be explicitly electrical, not shaft power or inferred efficiency.
A positive pressure margin is not proof the system operates at the prescribed flow.
"""
import math


def positive(x,zero=False):
    return type(x) in (int,float) and math.isfinite(x) and (x>=0 if zero else x>0)


def screen_curve(curve,flow_m3_s,required_pressure_Pa,pressure_basis,conditions):
    if not isinstance(curve,dict) or not positive(flow_m3_s) or not positive(required_pressure_Pa,True):
        raise ValueError('Explicit curve and finite positive demand/nonnegative pressure required')
    if pressure_basis not in ('fan_static','fan_total') or curve.get('pressure_basis')!=pressure_basis:
        raise ValueError('Fan-static and fan-total pressure cannot be mixed or automatically converted')
    if curve.get('power_basis')!='electrical_input':
        raise ValueError('Electrical-input power curve required; shaft/motor rated power is not interchangeable')
    if not isinstance(curve.get('source_ref'),str) or not curve['source_ref'].strip():
        raise ValueError('Specific model/selection provenance required')
    expected=curve.get('conditions')
    if not isinstance(expected,dict) or not isinstance(conditions,dict) or set(expected)!=set(conditions):
        raise ValueError('Explicit matching fan test/application conditions required')
    if not {'density_kg_m3','speed_rpm','installation_category'}<=set(expected):
        raise ValueError('Density speed and installation category required')
    if not positive(expected['density_kg_m3']) or not positive(expected['speed_rpm']) or not isinstance(expected['installation_category'],str) or not expected['installation_category'].strip():
        raise ValueError('Invalid fan curve conditions')
    if expected!=conditions:
        raise ValueError('Conditions differ; no automatic fan-law/density correction')
    interval=curve.get('stable_flow_interval_m3_s')
    if not isinstance(interval,list) or len(interval)!=2 or not all(positive(x,True) for x in interval) or interval[0]>=interval[1]:
        raise ValueError('Source-qualified stable interval required; not inferred from pressure shape')
    points=curve.get('points')
    if not isinstance(points,list) or len(points)<2:
        raise ValueError('At least two explicit tabulated curve points required')
    for p in points:
        if not isinstance(p,dict) or not positive(p.get('flow_m3_s'),True) or not positive(p.get('pressure_Pa'),True) or not positive(p.get('electrical_power_W')):
            raise ValueError('Finite SI flow pressure electrical power points required')
    flows=[p['flow_m3_s'] for p in points]
    if any(b<=a for a,b in zip(flows,flows[1:])):
        raise ValueError('Points must be supplied in strictly increasing flow order; no silent sorting')
    if interval[0]<flows[0] or interval[1]>flows[-1]:
        raise ValueError('Stable interval must lie inside tabulated support')
    if flow_m3_s<flows[0] or flow_m3_s>flows[-1]:
        return {'status':'FAIL_OUTSIDE_CURVE_SUPPORT','flow_m3_s':flow_m3_s,'electrical_power_W':None,'equilibrium_certified':False}
    if flow_m3_s<interval[0] or flow_m3_s>interval[1]:
        return {'status':'FAIL_OUTSIDE_STABLE_INTERVAL','flow_m3_s':flow_m3_s,'electrical_power_W':None,'equilibrium_certified':False}
    first=next(i for i in range(len(points)-1) if flows[i]<=flow_m3_s<=flows[i+1])
    left,right=points[first],points[first+1]
    fraction=(flow_m3_s-left['flow_m3_s'])/(right['flow_m3_s']-left['flow_m3_s'])
    pressure=left['pressure_Pa']+fraction*(right['pressure_Pa']-left['pressure_Pa'])
    power=left['electrical_power_W']+fraction*(right['electrical_power_W']-left['electrical_power_W'])
    if not math.isfinite(pressure) or not math.isfinite(power):
        raise ValueError('Nonfinite curve interpolation')
    margin=pressure-required_pressure_Pa
    return {'status':'PASS_FIXED_CURVE_CAPACITY_SCREEN_ONLY' if margin>=0 else 'FAIL_INSUFFICIENT_PRESSURE',
        'flow_m3_s':flow_m3_s,'curve_pressure_Pa':pressure,'required_pressure_Pa':required_pressure_Pa,
        'pressure_margin_Pa':margin,'electrical_power_W':power,'pressure_basis':pressure_basis,
        'interpolation':'PIECEWISE_LINEAR_NO_EXTRAPOLATION','curve_bracket_indices':[first,first+1],
        'source_ref':curve['source_ref'],'equilibrium_certified':False,'flow_control_or_balancing_certified':False,
        'scope':'FIXED_SPEED_CURVE_AT_PRESCRIBED_FLOW; NOT_ACTUAL_OPERATING_POINT_OR_ANNUAL_ENERGY'}
