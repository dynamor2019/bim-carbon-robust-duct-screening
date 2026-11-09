"""Spatial input identity contract. No routing solver or engineering certification."""
import hashlib
import json
import math


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()


def bind(domain, endpoints, sections, candidates, design_scenarios, held_out_scenarios, objective):
    """Bind explicit payloads; scenario/candidate order ignored, content retained."""
    for name, payload in [('domain',domain), ('endpoints',endpoints), ('sections',sections)]:
        if not isinstance(payload,dict) or not payload:
            raise ValueError(name+' requires nonempty explicit metadata')
    if domain.get('coordinate_unit')!='m' or domain.get('qualification')!='QUALIFIED_SPATIAL_DOMAIN':
        raise ValueError('Explicit metre domain qualification required; caller supplies evidence')
    if not domain.get('evidence_hashes') or not domain.get('admissibility_rule'):
        raise ValueError('Domain evidence and admissibility rule required')
    if not endpoints.get('fixed') or not endpoints.get('points'):
        raise ValueError('Fixed explicit endpoints required')
    if not sections.get('options') or not sections.get('envelope_rule'):
        raise ValueError('Explicit section options and envelope rule required')
    if not isinstance(candidates,list) or not candidates:
        raise ValueError('Nonempty candidates required')
    ids=[c.get('id') for c in candidates]
    if any(not isinstance(i,str) or not i.strip() for i in ids) or len(set(ids))!=len(ids):
        raise ValueError('Unique nonempty candidate IDs required')
    for c in candidates:
        if set(c)!= {'id','geometry','section_assignment'} or not c['geometry'] or not c['section_assignment']:
            raise ValueError('Each candidate requires only ID geometry and section assignment')
    for scenario_set in (design_scenarios,held_out_scenarios):
        if not isinstance(scenario_set,dict) or not scenario_set or any(not isinstance(k,str) or not k.strip() for k in scenario_set):
            raise ValueError('Nonempty scenario payload maps required')
        if any(not isinstance(v,dict) or not v for v in scenario_set.values()):
            raise ValueError('Scenario payloads cannot be empty')
    if set(design_scenarios)&set(held_out_scenarios):
        raise ValueError('Design and holdout IDs overlap')
    if not isinstance(objective,dict) or objective.get('metric') not in ('route_length','geometric_envelope_volume'):
        raise ValueError('Only explicit spatial metrics supported')
    unit={'route_length':'m','geometric_envelope_volume':'m3'}[objective['metric']]
    if objective.get('unit')!=unit or not objective.get('definition'):
        raise ValueError('Metric definition and compatible unit required')
    bindings={name:fingerprint(value) for name,value in [
        ('domain',domain),('endpoints',endpoints),('sections',sections),
        ('candidates',sorted(candidates,key=lambda c:c['id'])),
        ('design_scenarios',design_scenarios),('held_out_scenarios',held_out_scenarios),('objective',objective)]}
    return {'scope':'SUPPLIED_SPATIAL_PAYLOAD_IDENTITY_ONLY','bindings':bindings,
        'candidate_ids':sorted(ids),'formal_experiment':False,'scientific_validation':False}


def selection_record(binding, selected):
    if selected not in binding['candidate_ids']:
        raise ValueError('Selected candidate absent')
    return {'selected':selected,'binding_sha256':fingerprint(binding),
        'scope':'FIXED_IDENTITY_NOT_PROOF_OF_HIDDEN_HOLDOUT'}


def check_holdout_identity(binding, record):
    if record.get('binding_sha256')!=fingerprint(binding) or record.get('selected') not in binding['candidate_ids']:
        raise ValueError('Candidate domain scenario or objective identity changed')
    return True
