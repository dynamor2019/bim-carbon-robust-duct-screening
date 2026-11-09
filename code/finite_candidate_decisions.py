"""Exact selection over supplied finite candidates; no routing generation or physics defaults.

Costs are in one caller-declared common unit. Scenario infeasibility excludes a
candidate from robust selection, never converted to zero or silently dropped.
Scenario optima are conditional on this candidate set, not global route optima.
"""
import math
from dataclasses import dataclass
from itertools import product


@dataclass(frozen=True)
class Evaluation:
    feasible: bool
    cost: float | None


class NoFeasibleDesign(ValueError):
    pass


def validate(evaluations,scenarios):
    if not isinstance(evaluations,dict) or not evaluations:
        raise ValueError('Nonempty candidate evaluations required')
    if not scenarios or len(set(scenarios))!=len(scenarios):
        raise ValueError('Nonempty unique scenario IDs required')
    if not all(isinstance(s,str) and s.strip() for s in scenarios):
        raise ValueError('Scenario IDs must be nonempty strings')
    for design,rows in evaluations.items():
        if not isinstance(design,str) or not design.strip() or not isinstance(rows,dict):
            raise ValueError('Candidate IDs and evaluation maps required')
        if set(rows)!=set(scenarios):
            raise ValueError('Every candidate needs every declared scenario; missing/extra evaluations rejected')
        for row in rows.values():
            if not isinstance(row,Evaluation) or type(row.feasible) is not bool:
                raise ValueError('Typed feasibility flag required')
            if row.feasible and (isinstance(row.cost,bool) or not isinstance(row.cost,(int,float)) or not math.isfinite(row.cost)):
                raise ValueError('Feasible design requires finite numeric cost')
            if not row.feasible and row.cost is not None:
                raise ValueError('Infeasible objective must be null, not a penalty or favorable number')


def select(evaluations,scenarios,mode,nominal=None):
    validate(evaluations,scenarios)
    if mode not in ('deterministic','minimax','minimax_regret'):
        raise ValueError('Unknown objective')
    if mode=='deterministic' and nominal not in scenarios:
        raise ValueError('Declared nominal scenario required')
    optima={s:min((rows[s].cost for rows in evaluations.values() if rows[s].feasible),default=None) for s in scenarios}
    required=[nominal] if mode=='deterministic' else list(scenarios)
    eligible=sorted(d for d,rows in evaluations.items() if all(rows[s].feasible for s in required))
    if not eligible:
        raise NoFeasibleDesign('No candidate satisfies required scenarios; keep infeasibility outcome')
    scores={}
    for design in eligible:
        rows=evaluations[design]
        if mode=='deterministic':
            score=rows[nominal].cost
        elif mode=='minimax':
            score=max(rows[s].cost for s in scenarios)
        else:
            score=max(rows[s].cost-optima[s] for s in scenarios)
        scores[design]=score
    optimum=min(scores.values())
    tied=sorted(d for d,score in scores.items() if score==optimum)
    return {'selected':tied[0],'tied_designs':tied,'objective':optimum,'scores':scores,
        'scenario_candidate_optima':optima,'eligible':eligible,'excluded':sorted(set(evaluations)-set(eligible)),
        'mode':mode,'bound_scope':'EXACT_SUPPLIED_FINITE_CANDIDATE_SET_ONLY',
        'global_route_optimality_certified':False}


def enumerate_assignments(options_by_variable,maximum_candidates):
    """Bounded Cartesian enumeration; no silent truncation or partial pricing claims."""
    if not isinstance(options_by_variable,dict) or not options_by_variable:
        raise ValueError('Nonempty option map required')
    if type(maximum_candidates) is not int or maximum_candidates<1:
        raise ValueError('Positive explicit enumeration budget required')
    if not all(isinstance(k,str) and k.strip() for k in options_by_variable):
        raise ValueError('Variable keys must be nonempty strings')
    keys=sorted(options_by_variable)
    count=1
    for key in keys:
        options=options_by_variable[key]
        if not isinstance(options,(list,tuple)) or not options:
            raise ValueError('Every variable needs declared options')
        if len({repr(v) for v in options})!=len(options):
            raise ValueError('Duplicate options rejected')
        count*=len(options)
    if count>maximum_candidates:
        raise ValueError(f'Candidate count {count} exceeds explicit budget {maximum_candidates}; no partial set returned')
    return [dict(zip(keys,values)) for values in product(*(options_by_variable[k] for k in keys))]


def held_out_evaluate(evaluations,scenario_ids,design_scenario_ids,selected):
    """Evaluation only; caller cannot select a new design through this entry."""
    if set(scenario_ids)&set(design_scenario_ids):
        raise ValueError('Design and held-out scenario IDs overlap')
    validate(evaluations,scenario_ids)
    if selected not in evaluations:
        raise ValueError('Previously selected candidate absent')
    rows=[]
    for scenario in scenario_ids:
        row=evaluations[selected][scenario]
        best=min((v[scenario].cost for v in evaluations.values() if v[scenario].feasible),default=None)
        rows.append({'scenario':scenario,'feasible':row.feasible,'cost':row.cost,
            'candidate_set_optimum':best,'regret':row.cost-best if row.feasible else None,
            'regret_scope':'SUPPLIED_CANDIDATES_ONLY'})
    return {'selected':selected,'scenarios':rows,'failure_count':sum(not r['feasible'] for r in rows),
        'feasibility_fraction':sum(r['feasible'] for r in rows)/len(rows),
        'maximum_regret_all_scenarios':max(r['regret'] for r in rows) if all(r['feasible'] for r in rows) else None,
        'selected_using_held_out':False}
