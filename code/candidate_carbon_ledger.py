"""Explicit selected-stage ledger, not a complete LCA or project input qualification.
B4 events here include declared replacement production only. Other B4 burdens
must be included separately in a reviewed boundary or acknowledged as excluded.
"""
import math


def finite(x,nonnegative=False):
    return type(x) in (int,float) and math.isfinite(x) and (not nonnegative or x>=0)


def factor(record,indicator,unit,module):
    if not isinstance(record,dict) or record.get('state')!='DECLARED':
        raise ValueError('Missing/MND/MNR factors are not zero; selected factor must be declared')
    if record.get('indicator')!=indicator or record.get('unit')!=unit or record.get('module')!=module:
        raise ValueError('Factor indicator declared unit and stage mismatch')
    if not finite(record.get('value')) or not isinstance(record.get('source_ref'),str) or not record['source_ref'].strip():
        raise ValueError('Finite explicitly sourced factor required; negative declared values are retained')
    return record['value']


def ledger(components,operating_periods,horizon_years,indicator,boundary):
    if indicator not in ('GWP-total','GWP-fossil') or not finite(horizon_years,True) or horizon_years<=0:
        raise ValueError('Explicit indicator and positive analysis horizon required')
    if not isinstance(boundary,dict) or boundary.get('modules')!=['A1-A3','B4','B6'] or boundary.get('replacement_scope')!='PRODUCTION_ONLY':
        raise ValueError('Explicit selected-stage and replacement-production boundary required')
    if not isinstance(boundary.get('excluded_burdens'),list) or not boundary['excluded_burdens'] or not isinstance(boundary.get('source_ref'),str) or not boundary['source_ref'].strip():
        raise ValueError('Replacement/other excluded burdens and accounting provenance must be explicit')
    if not isinstance(components,list) or not components or not isinstance(operating_periods,list) or not operating_periods:
        raise ValueError('Nonempty material and operating-period records required; missing is not zero')
    ids=set()
    rows=[]
    for component in components:
        if not isinstance(component,dict):
            raise ValueError('Typed component required')
        key=component.get('id')
        if not isinstance(key,str) or not key.strip() or key in ids:
            raise ValueError('Unique component IDs required')
        ids.add(key)
        mass=component.get('mass_kg')
        if not finite(mass,True) or not isinstance(component.get('mass_ref'),str) or not component['mass_ref'].strip():
            raise ValueError('Explicit nonnegative material mass and provenance required')
        initial=factor(component.get('initial_factor'),indicator,'kgCO2e/kg','A1-A3')*mass
        events=component.get('replacement_events')
        if not isinstance(events,list):
            raise ValueError('Explicit replacement events required; no lifetime or default count inferred')
        times=[]
        replacements=[]
        for event in events:
            if not isinstance(event,dict):
                raise ValueError('Typed replacement event required')
            year=event.get('year')
            replacement_mass=event.get('mass_kg')
            if not finite(year) or not 0<year<horizon_years or year in times:
                raise ValueError('Unique replacement times must lie strictly inside horizon; horizon-end replacement excluded explicitly')
            if not finite(replacement_mass,True) or not isinstance(event.get('source_ref'),str) or not event['source_ref'].strip():
                raise ValueError('Replacement mass and event provenance required')
            times.append(year)
            carbon=replacement_mass*factor(event.get('factor'),indicator,'kgCO2e/kg','A1-A3')
            replacements.append({'year':year,'mass_kg':replacement_mass,'production_carbon_kgCO2e':carbon})
        rows.append({'component_id':key,'A1-A3_kgCO2e':initial,'B4_replacement_production_kgCO2e':sum(e['production_carbon_kgCO2e'] for e in replacements),'events':replacements})
    periods=[]
    ordered=[]
    period_ids=set()
    for period in operating_periods:
        if not isinstance(period,dict):
            raise ValueError('Typed operating period required')
        key=period.get('id')
        start,end=period.get('start_year'),period.get('end_year')
        energy=period.get('electricity_kWh')
        if not isinstance(key,str) or not key.strip() or key in period_ids:
            raise ValueError('Unique period IDs required')
        period_ids.add(key)
        if not finite(start,True) or not finite(end) or not start<end<=horizon_years:
            raise ValueError('Periods must lie inside horizon')
        if not finite(energy,True) or not isinstance(period.get('energy_ref'),str) or not period['energy_ref'].strip():
            raise ValueError('Explicit energy amount and qualified model/duty provenance required; no hours default')
        carbon=energy*factor(period.get('grid_factor'),indicator,'kgCO2e/kWh','B6')
        periods.append({'id':key,'start_year':start,'end_year':end,'electricity_kWh':energy,'B6_kgCO2e':carbon})
        ordered.append((start,end))
    ordered.sort()
    if ordered[0][0]!=0 or ordered[-1][1]!=horizon_years or any(a[1]!=b[0] for a,b in zip(ordered,ordered[1:])):
        raise ValueError('Operating periods must cover entire horizon without overlaps or gaps')
    a=sum(r['A1-A3_kgCO2e'] for r in rows)
    b=sum(r['B4_replacement_production_kgCO2e'] for r in rows)
    c=sum(r['B6_kgCO2e'] for r in periods)
    if not all(math.isfinite(x) for x in (a,b,c,a+b+c)):
        raise ValueError('Nonfinite ledger calculation')
    return {'indicator':indicator,'horizon_years':horizon_years,'components':rows,'operating_periods':periods,
        'totals':{'A1-A3_kgCO2e':a,'B4_replacement_production_kgCO2e':b,'B6_kgCO2e':c,'selected_stage_sum_kgCO2e':a+b+c},
        'boundary':boundary,'whole_life_LCA':False,'installed_product_applicability_certified':False,
        'actual_operating_energy_certified':False,'scope':'DECLARED_FACTORS_AND_ENERGY_SELECTED_STAGE_ARITHMETIC_ONLY'}
