"""Enumerate intersections of supplied piecewise-linear fan/system pressure curves.
No system-curve generation, air control design or nonlinear dynamics certification.
"""
import math


def validate_curve(points):
    if not isinstance(points,list) or len(points)<2:
        raise ValueError('At least two supplied curve points required')
    for p in points:
        if not isinstance(p,dict) or not all(type(p.get(k)) in (int,float) and math.isfinite(p[k]) and p[k]>=0 for k in ('flow_m3_s','pressure_Pa')):
            raise ValueError('Finite nonnegative SI curve points required')
    if any(b['flow_m3_s']<=a['flow_m3_s'] for a,b in zip(points,points[1:])):
        raise ValueError('Strictly increasing supplied flow order required')


def value_and_slope(points,q):
    for i,(a,b) in enumerate(zip(points,points[1:])):
        if a['flow_m3_s']<=q<=b['flow_m3_s']:
            slope=(b['pressure_Pa']-a['pressure_Pa'])/(b['flow_m3_s']-a['flow_m3_s'])
            result=a['pressure_Pa']+slope*(q-a['flow_m3_s'])
            if not math.isfinite(slope) or not math.isfinite(result):
                raise ValueError('Nonfinite interpolation/slope')
            return result,slope
    raise ValueError('Outside curve support; no extrapolation')


def intersections(fan,system,pressure_basis,pressure_tolerance_Pa,flow_tolerance_m3_s):
    if pressure_basis not in ('fan_static','fan_total') or not isinstance(fan,dict) or not isinstance(system,dict):
        raise ValueError('Explicit same-basis curve records required')
    if fan.get('pressure_basis')!=pressure_basis or system.get('pressure_basis')!=pressure_basis:
        raise ValueError('Pressure convention mismatch')
    if fan.get('conditions')!=system.get('conditions') or not isinstance(fan.get('conditions'),dict) or not fan['conditions']:
        raise ValueError('Matching explicit curve conditions required')
    if not all(isinstance(c.get('source_ref'),str) and c['source_ref'].strip() for c in (fan,system)):
        raise ValueError('Separate fan/system provenance references required')
    if not all(type(x) in (int,float) and math.isfinite(x) and x>0 for x in (pressure_tolerance_Pa,flow_tolerance_m3_s)):
        raise ValueError('Explicit positive numerical tolerances required')
    f,s=fan.get('points'),system.get('points')
    validate_curve(f)
    validate_curve(s)
    low=max(f[0]['flow_m3_s'],s[0]['flow_m3_s'])
    high=min(f[-1]['flow_m3_s'],s[-1]['flow_m3_s'])
    if low>=high:
        return {'status':'NO_COMMON_INTERVAL','points':[],'coincident_intervals':[],'actual_operation_certified':False}
    knots=sorted({low,high}|{p['flow_m3_s'] for p in f+s if low<p['flow_m3_s']<high})
    roots=[]
    intervals=[]
    segment_rows=[]
    for a,b in zip(knots,knots[1:]):
        fa,_=value_and_slope(f,a)
        sa,_=value_and_slope(s,a)
        fb,_=value_and_slope(f,b)
        sb,_=value_and_slope(s,b)
        da,db=fa-sa,fb-sb
        mid=(a+b)/2
        _,fs=value_and_slope(f,mid)
        _,ss=value_and_slope(s,mid)
        segment_rows.append({'from_m3_s':a,'to_m3_s':b,'fan_minus_system_slope_Pa_per_m3_s':fs-ss})
        if abs(da)<=pressure_tolerance_Pa and abs(db)<=pressure_tolerance_Pa:
            intervals.append({'from_m3_s':a,'to_m3_s':b,'status':'COINCIDENT_WITHIN_NUMERICAL_TOLERANCE'})
            continue
        if abs(da)<=pressure_tolerance_Pa:
            roots.append(a)
        if abs(db)<=pressure_tolerance_Pa:
            roots.append(b)
        if da*db<0:
            roots.append(a+(b-a)*(-da)/(db-da))
    roots.sort()
    unique=[]
    for q in roots:
        if not unique or q-unique[-1]>flow_tolerance_m3_s:
            unique.append(q)
    points=[]
    for q in unique:
        pressure,_=value_and_slope(f,q)
        system_pressure,_=value_and_slope(s,q)
        # At a knot retain both adjacent slopes, do not choose an arbitrary side.
        slopes=[r['fan_minus_system_slope_Pa_per_m3_s'] for r in segment_rows if r['from_m3_s']-flow_tolerance_m3_s<=q<=r['to_m3_s']+flow_tolerance_m3_s]
        stable=all(x<0 for x in slopes)
        points.append({'flow_m3_s':q,'fan_pressure_Pa':pressure,'system_pressure_Pa':system_pressure,
            'residual_Pa':pressure-system_pressure,'adjacent_net_slopes_Pa_per_m3_s':slopes,
            'negative_net_slope_on_all_adjacent_segments':stable})
    status='AMBIGUOUS_COINCIDENT_INTERVAL' if intervals else ('NO_INTERSECTION' if not points else ('MULTIPLE_INTERSECTIONS' if len(points)>1 else 'UNIQUE_NUMERICAL_INTERSECTION'))
    return {'status':status,'points':points,'coincident_intervals':intervals,'common_support_m3_s':[low,high],
        'pressure_tolerance_Pa':pressure_tolerance_Pa,'flow_tolerance_m3_s':flow_tolerance_m3_s,
        'actual_operation_certified':False,'dynamic_stability_certified':False,
        'scope':'ALL_INTERSECTIONS_OF_SUPPLIED_PIECEWISE_LINEAR_CURVES_WITHIN_COMMON_SUPPORT'}
