"""Freeze source-bound local geometry candidates; never certify unknown ports/space."""
import hashlib
import json
import math
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def point(v):
    return isinstance(v,list) and len(v)==3 and all(type(x) in (int,float) and math.isfinite(x) for x in v)


def local_candidate(inventory):
    eligible=[]
    rejected=[]
    for c in inventory['components']:
        if c.get('ifc_type')!='IfcDuctSegment':
            continue
        axes=c.get('axes',[])
        if c.get('method')!='source_circular_extrusion' or len(axes)!=1:
            rejected.append({'ifc_id':c['ifc_id'],'reason':'NOT_SINGLE_SOURCE_CIRCULAR_AXIS'})
            continue
        a=axes[0]
        if not point(a.get('end_a_m')) or not point(a.get('end_b_m')):
            rejected.append({'ifc_id':c['ifc_id'],'reason':'INVALID_ENDPOINT'})
            continue
        length=math.dist(a['end_a_m'],a['end_b_m'])
        radius=a.get('source_outer_radius_m')
        if length<=0 or type(radius) not in (int,float) or not math.isfinite(radius) or radius<=0:
            rejected.append({'ifc_id':c['ifc_id'],'reason':'NONPOSITIVE_AXIS_OR_RADIUS'})
            continue
        if not point(c.get('bbox_min_m')) or not point(c.get('bbox_max_m')) or any(x>=y for x,y in zip(c['bbox_min_m'],c['bbox_max_m'])):
            rejected.append({'ifc_id':c['ifc_id'],'reason':'INVALID_BBOX'})
            continue
        eligible.append((length,c,a))
    if not eligible:
        raise ValueError('No nonzero source circular segment: do not fabricate a local domain')
    length,c,a=sorted(eligible,key=lambda x:(-x[0],x[1]['ifc_id']))[0]
    return c,a,length,rejected,len(eligible)


def freeze_local(inventory,independent,architecture,registration,contract):
    c,a,length,rejected,count=local_candidate(inventory)
    ports=[{'id':str(c['ifc_id'])+':axis-'+name,'center_m':a[key],
            'geometric_status':'SOURCE_AXIS_REFERENCE','engineering_status':'UNKNOWN',
            'main_analysis':'EXCLUDED_UNCERTIFIED_PORT','sensitivity_use':'FIXED_GEOMETRIC_ENDPOINT_ONLY',
            'required_evidence':'Explicit design-interface adoption or native connector/service certificate; do not infer direction'}
           for name,key in [('a','end_a_m'),('b','end_b_m')]]
    excluded=[{'kind':'PORT','id':p['id'],'reason':p['main_analysis']} for p in ports]
    spaces=[]
    for model in architecture.get('models',[]):
        for space in model.get('spaces',[]):
            spaces.append({'source':model['source'],'ifc_id':space['ifc_id'],'guid':space.get('guid'),
                'geometry_status':space.get('status'),'main_analysis':'EXCLUDED_UNCERTIFIED_REGISTERED_OBSTACLE_OR_PASSAGE',
                'required_evidence':'Validated HVAC registration, geometric integrity and obstacle/passage/installation rule',
                'local_intersection':'NOT_TESTED_UNREGISTERED_LAYER'})
    excluded.extend(spaces)
    excluded.extend([
        {'kind':'SPATIAL_DOMAIN','reason':'SOURCE_DUCT_BBOX_IS_ROI_NOT_AVAILABLE_FREE_SPACE',
         'required_evidence':'Registered architecture/structure/installation envelope and admissibility rules'},
        {'kind':'SECTION_OPTIONS','reason':'SOURCE_SIZE_NOT_QUALIFIED_ALTERNATIVE_CATALOGUE',
         'required_evidence':'Explicit candidate section catalogue and geometric envelope; no capacity/energy claim'}])
    overlapping=[]
    lo,hi=c['bbox_min_m'],c['bbox_max_m']
    for other in inventory['components']:
        if other['ifc_id']==c['ifc_id']:continue
        ol,oh=other.get('bbox_min_m'),other.get('bbox_max_m')
        if point(ol) and point(oh) and all(x<=v and u<=y for x,y,u,v in zip(lo,hi,ol,oh)):
            overlapping.append({'ifc_id':other['ifc_id'],'guid':other.get('guid'),'ifc_type':other.get('ifc_type'),
                'bbox_min_m':ol,'bbox_max_m':oh,'status':'BBOX_INTERSECTION_CANDIDATE_NOT_SOLID_CLASH',
                'main_analysis':'EXCLUDED_UNKNOWN_OBSTACLE_ROLE'})
    return {'artifact_type':'source_bound_local_spatial_candidate_freeze',
        'status':'FROZEN_CANDIDATE_SNAPSHOT_NOT_QUALIFIED_FEASIBLE_DOMAIN',
        'selection_rule':'Longest positive single-source circular extrusion in Concrete302PK01 cache; tie lower IFC ID; no optimization outcomes used',
        'selection_pool_count':count,'model_id':inventory['model_id'],'source_ifc_sha256':inventory['sourceSha256'],
        'selected_source':{'ifc_id':c['ifc_id'],'guid':c['guid'],'mesh_path':c['mesh_path'],'mesh_sha256':c['mesh_sha256'],
            'method':c['method'],'axis_length_m':length,'end_a_m':a['end_a_m'],'end_b_m':a['end_b_m']},
        'coordinate_unit':'m','coordinate_scope':'HVAC source world coordinates, no second transform',
        'roi':{'bbox_min_m':lo,'bbox_max_m':hi,'padding_m':0,'status':'OBSERVED_DUCT_BBOX_NOT_FREE_SPACE'},
        'endpoints':ports,'sections':[{'shape':'circular','outer_diameter_m':2*a['source_outer_radius_m'],
            'status':'OBSERVED_SOURCE_GEOMETRY_ONLY','alternative_sizes':[], 'main_analysis':'EXCLUDED_UNQUALIFIED_CATALOGUE'}],
        'obstacle_candidates':overlapping,'architecture_quarantine':spaces,
        'architecture_invalid_space_count':architecture.get('invalid_space_count'),
        'registration_status':registration['status'],'inventory_audit_status':independent['status'],
        'excluded':excluded,'selection_pool_rejected':rejected,
        'main_analysis':{'domain':None,'endpoints':[],'sections':[],'candidates':[],
            'ready_for_contract_binding':False,'reason':'UNKNOWN_PORTS_REGISTERED_DOMAIN_AND_SECTION_CATALOGUE'},
        'sensitivity_candidate':{'scope':'SOURCE_GEOMETRIC_ENDPOINTS_AND_ENVELOPE_ONLY_NOT_SERVICE',
            'geometry':[a['end_a_m'],a['end_b_m']],'section_assignment':[str(2*a['source_outer_radius_m'])],
            'not_executable_routing_scenario':True},
        'non_reportable':contract['non_reportable'],'formal_experiment':False,'scientific_validation':False}


def main():
    p=Path(__file__).resolve().parent.parent;r=p/'milestones/reproducibility'
    files=[r/'network-interfaces/concrete-interfaces.json',r/'network-interfaces/independent-interface-audit.json',
        r/'upper-storey-native-scope-audit.json',r/'alignment-registration-audit.json',r/'spatial-comparison-contract.json']
    data=[json.loads(f.read_text(encoding='utf-8')) for f in files]
    expected=data[1]['inputHashes']['concrete-interfaces.json']
    if sha(files[0])!=expected or data[1]['status']!='PASS_CANDIDATE_INVENTORIES_ONLY':
        raise ValueError('Inventory does not match audited candidate snapshot')
    report=freeze_local(*data)
    mesh=Path(report['selected_source']['mesh_path'])
    if sha(mesh)!=report['selected_source']['mesh_sha256']:
        raise ValueError('Source mesh hash mismatch')
    report['codeSha256']=sha(Path(__file__))
    report['source_files']=[{'path':str(f),'sha256':sha(f)} for f in files]+[{'path':str(mesh),'sha256':sha(mesh)}]
    (r/'local-spatial-domain-freeze.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'selected_source':report['selected_source'],
        'selection_pool_count':report['selection_pool_count'],'architecture_quarantine_count':len(report['architecture_quarantine']),
        'bbox_obstacle_candidates':len(report['obstacle_candidates']),'main_analysis_candidate_count':0},indent=2))


if __name__=='__main__':main()
