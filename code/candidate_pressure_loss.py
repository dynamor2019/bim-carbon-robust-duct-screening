"""Explicit steady circular straight-duct and nonnegative loss arithmetic.
No f/rho/K defaults, Reynolds model, tee coefficient inference or fan sizing.
"""
import math


def number(value,nonnegative=False):
    return type(value) in (int,float) and math.isfinite(value) and (value>=0 if nonnegative else value>0)


def segment_loss(flow_m3_s,length_m,diameter_m,density_kg_m3,darcy_factor,local_losses,friction_ref):
    if not number(flow_m3_s,True) or not all(number(x) for x in (length_m,diameter_m,density_kg_m3,darcy_factor)):
        raise ValueError('Explicit finite SI flow/length/diameter/density and positive Darcy factor required')
    if not isinstance(friction_ref,str) or not friction_ref.strip() or not isinstance(local_losses,list):
        raise ValueError('Friction provenance and explicit local-loss list required; empty list is an explicit no-local-loss model')
    area=math.pi*diameter_m**2/4
    if not math.isfinite(area) or area<=0:
        raise ValueError('Area overflow/underflow')
    velocity=flow_m3_s/area
    dynamic=density_kg_m3*velocity**2/2
    friction=darcy_factor*(length_m/diameter_m)*dynamic
    losses=[]
    ids=set()
    for record in local_losses:
        if not isinstance(record,dict):
            raise ValueError('Explicit local loss record required')
        key=record.get('id')
        if not isinstance(key,str) or not key.strip() or key in ids:
            raise ValueError('Unique local loss IDs required')
        ids.add(key)
        coefficient=record.get('coefficient')
        reference_velocity=record.get('reference_velocity_m_s')
        if not number(coefficient,True) or not number(reference_velocity,True):
            raise ValueError('Finite nonnegative coefficient and explicit reference velocity required; signed branch models unsupported')
        if not isinstance(record.get('reference'),str) or not record['reference'].strip():
            raise ValueError('Local coefficient/reference-section provenance required')
        pressure=coefficient*density_kg_m3*reference_velocity**2/2
        losses.append({'id':key,'pressure_loss_Pa':pressure,'reference_velocity_m_s':reference_velocity,'coefficient':coefficient,'reference':record['reference']})
    total=friction+sum(r['pressure_loss_Pa'] for r in losses)
    if not all(math.isfinite(x) for x in (velocity,dynamic,friction,total)):
        raise ValueError('Nonfinite pressure calculation')
    return {'flow_m3_s':flow_m3_s,'velocity_m_s':velocity,'dynamic_pressure_Pa':dynamic,'friction_loss_Pa':friction,
        'local_losses':losses,'total_pressure_loss_Pa':total,'friction_ref':friction_ref,
        'scope':'STEADY_EXPLICIT_DARCY_AND_NONNEGATIVE_LOCAL_LOSS_ARITHMETIC'}


def path_requirements(terminal_paths,edge_losses,terminal_boundary_losses,root_boundary_loss):
    if not isinstance(terminal_paths,dict) or not terminal_paths or not isinstance(edge_losses,dict):
        raise ValueError('Explicit paths and edge losses required')
    if not isinstance(terminal_boundary_losses,dict) or set(terminal_boundary_losses)!=set(terminal_paths):
        raise ValueError('Every terminal needs an explicit boundary loss; missing is not zero')
    if not number(root_boundary_loss,True) or not all(number(x,True) for x in terminal_boundary_losses.values()):
        raise ValueError('Finite nonnegative explicit boundary losses required')
    used=set()
    rows=[]
    for terminal,path in sorted(terminal_paths.items()):
        if not isinstance(path,list) or not path or not all(isinstance(e,str) for e in path) or len(set(path))!=len(path):
            raise ValueError('Nonempty simple edge path required')
        if not set(path)<=set(edge_losses):
            raise ValueError('Path references missing pressure losses')
        if not all(number(edge_losses[e],True) for e in path):
            raise ValueError('Finite nonnegative edge losses required')
        used.update(path)
        loss=sum(edge_losses[e] for e in path)+terminal_boundary_losses[terminal]+root_boundary_loss
        if not math.isfinite(loss):
            raise ValueError('Nonfinite path requirement')
        rows.append({'terminal':terminal,'path':path,'path_requirement_Pa':loss})
    if used!=set(edge_losses):
        raise ValueError('Unreferenced edge losses rejected')
    maximum=max(r['path_requirement_Pa'] for r in rows)
    return {'paths':rows,'maximum_path_requirement_Pa':maximum,
        'additional_balancing_loss_Pa':{r['terminal']:maximum-r['path_requirement_Pa'] for r in rows},
        'balanced_network_certified':False,'fan_pressure_rise_certified':False,
        'scope':'SUPPLIED_PATH_LOSS_SUM_ONLY; BALANCING_VALUES_ARE_ARITHMETIC_GAPS_NOT_DESIGNED_DAMPERS'}
