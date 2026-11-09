"""Recompute AHU duct source axes and screen all fittings/accessories around the observed gap."""
import json
from pathlib import Path
from collections import Counter
import numpy as np
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.unit
import ifcopenshell.util.element
from verify_paired_boundary import extrusion_axes
from trace_source_boundary import group_memberships,simple
from audit_AHU_neighborhood_interfaces import bbox_gap
from mesh_diagnostics import nearest_surface
from recover_fitting_interfaces import sha


def rim_samples(center,normal,radius,count=16):
    normal=np.array(normal,float)
    normal=normal/np.linalg.norm(normal)
    reference=np.eye(3)[np.argmin(abs(normal))]
    first=np.cross(normal,reference)
    first/=np.linalg.norm(first)
    second=np.cross(normal,first)
    angle=np.arange(count)*2*np.pi/count
    return np.array(center)+radius*(np.cos(angle)[:,None]*first+np.sin(angle)[:,None]*second)


def body_types(entity):
    counts=Counter()
    def visit(item):
        counts[item.is_a()]+=1
        if item.is_a('IfcMappedItem'):
            for child in item.MappingSource.MappedRepresentation.Items:
                visit(child)
        elif item.is_a('IfcBooleanResult'):
            visit(item.FirstOperand)
            visit(item.SecondOperand)
    for representation in entity.Representation.Representations:
        if representation.RepresentationIdentifier=='Body':
            for item in representation.Items:
                visit(item)
    return dict(counts)


def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'milestones/reproducibility'
    neighborhood_path=root/'AHU-neighborhood-interface-audit.json'
    offset_path=root/'AHU-rim-offset-review.json'
    data=json.loads(neighborhood_path.read_text(encoding='utf-8'))
    offsets=json.loads(offset_path.read_text(encoding='utf-8'))
    models=[]
    sources=data['source_files']
    for model,offset_model,source_record in zip(data['models'],offsets['models'],sources):
        path=Path(source_record['path'])
        if sha(path)!=source_record['sha256']:
            raise ValueError('Original source changed')
        print('Native gap sources and ungrouped fitting screen:',path.name,flush=True)
        source=ifcopenshell.open(str(path))
        scale=ifcopenshell.util.unit.calculate_unit_scale(source)
        settings=ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS,True)
        fan=source.by_id(model['fan_id'])
        shape=ifcopenshell.geom.create_shape(settings,fan)
        fan_vertices=np.array(shape.geometry.verts).reshape(-1,3)
        fan_faces=np.array(shape.geometry.faces).reshape(-1,3)
        fan_axes=extrusion_axes(fan,scale)
        checks=[]
        for pipe in offset_model['touching_bbox_duct_candidates']:
            entity=source.by_id(pipe['id'])
            axes=extrusion_axes(entity,scale)
            circle_axes=[a for a in axes if a['source_outer_radius_m'] is not None]
            comparisons=[]
            for axis in circle_axes:
                normal=np.array(axis['end_b_m'])-axis['end_a_m']
                for label in ('end_a_m','end_b_m'):
                    point=np.array(axis[label])
                    sample=rim_samples(point,normal,axis['source_outer_radius_m'])
                    distances=[nearest_surface(p,fan_vertices,fan_faces)['distance_m'] for p in sample]
                    comparisons.append({'solid_id':axis['solid_ifc_id'],'end_label':label,'center_m':point.tolist(),
                        'source_radius_m':axis['source_outer_radius_m'],'center_to_AHU_surface':nearest_surface(point,fan_vertices,fan_faces),
                        'perimeter_sample_count':len(sample),'sample_nearest_surface_distance_min_m':float(min(distances)),
                        'sample_nearest_surface_distance_max_m':float(max(distances))})
            checks.append({'pipe_id':entity.id(),'guid':entity.GlobalId,'groups':group_memberships(entity),
                'native_body_types':body_types(entity),'native_axes':axes,'source_end_surface_checks':comparisons})
        candidates=source.by_type('IfcDuctFitting')+source.by_type('IfcDuctSilencer')+source.by_type('IfcDamper')
        no_representation=[{'id':e.id(),'type':e.is_a(),'name':e.Name} for e in candidates if not e.Representation]
        unique={e.id():e for e in candidates if e.Representation}
        generated=set()
        hits=[]
        # Include all model fittings/accessories regardless of native system assignment.
        print('Raw source endpoints checked; generate all fitting/accessory meshes:',len(unique),flush=True)
        iterator=ifcopenshell.geom.iterator(settings,source,4,include=list(unique.values()))
        if iterator.initialize():
            while True:
                item=iterator.get()
                generated.add(item.id)
                if len(generated)%500==0:
                    print('Fitting/accessory meshes checked:',len(generated),'/',len(unique),flush=True)
                vertices=np.array(item.geometry.verts).reshape(-1,3)
                if not len(vertices) or not np.isfinite(vertices).all():
                    raise ValueError('Nonfinite fitting/accessory geometry')
                gap=bbox_gap(fan_vertices.min(axis=0),fan_vertices.max(axis=0),vertices.min(axis=0),vertices.max(axis=0))
                if gap<=.1:
                    entity=source.by_id(item.id)
                    hits.append({'id':entity.id(),'guid':entity.GlobalId,'type':entity.is_a(),'name':entity.Name,
                        'groups':group_memberships(entity),'bbox_separation_to_AHU_m':gap,
                        'bbox_min_m':vertices.min(axis=0).tolist(),'bbox_max_m':vertices.max(axis=0).tolist(),
                        'psets':simple(ifcopenshell.util.element.get_psets(entity))})
                if not iterator.next():
                    break
        failed=[{'id':e.id(),'type':e.is_a(),'name':e.Name} for key,e in unique.items() if key not in generated]
        models.append({'source':path.name,'fan_id':fan.id(),'AHU_native_body_types':body_types(fan),'AHU_source_axes':fan_axes,
            'pipe_checks':checks,'all_fitting_accessory_class_count':len(candidates),'no_representation':no_representation,'fitting_accessory_candidates':len(unique),'generated_count':len(generated),'not_generated':failed,
            'screen_bbox_separation_m':.1,'near_fitting_accessory_hits':hits})
        del iterator,source
        if sha(path)!=source_record['sha256']:
            raise ValueError('Original source changed')
    report={'artifact_type':'raw_native_AHU_gap_sources_and_all_model_fitting_accessory_screen','status':'GAP_SOURCE_DIAGNOSIS_ONLY',
        'inputHashes':{neighborhood_path.name:sha(neighborhood_path),offset_path.name:sha(offset_path)},'source_files':sources,
        'codeSha256':sha(Path(__file__)),'helperHashes':{name:sha(Path(__file__).with_name(name)) for name in ('verify_paired_boundary.py','trace_source_boundary.py','audit_AHU_neighborhood_interfaces.py','mesh_diagnostics.py')},
        'geometry_worker_threads':4,'models':models,'limitations':['Sixteen perimeter samples and endpoint surface distances are finite probes, not a complete surface-contact proof.',
            'Fitting/silencer/damper screen is bounded to these types; ungenerated objects retained and other classifications not excluded.',
            '0.1 m bbox screening range is not an engineering joint or adapter allowance.',
            'No inferred caps, adapters, offsets or source repairs; signed source direction is not airflow direction.']}
    (root/'AHU-native-gap-source-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'models':[{'source':m['source'],'AHU_body_types':m['AHU_native_body_types'],'AHU_axis_count':len(m['AHU_source_axes']),
        'pipes':[{'id':p['pipe_id'],'body_types':p['native_body_types'],'end_checks':[{'center_m':r['center_m'],'center_surface_distance_m':r['center_to_AHU_surface']['distance_m'],
            'rim_sample_min_m':r['sample_nearest_surface_distance_min_m'],'rim_sample_max_m':r['sample_nearest_surface_distance_max_m']} for r in p['source_end_surface_checks']]} for p in m['pipe_checks']],
        'fitting_candidates':m['fitting_accessory_candidates'],'generated_count':m['generated_count'],'not_generated_count':len(m['not_generated']),
        'near_fittings':[{'id':h['id'],'type':h['type'],'name':h['name'],'groups':[g['group_name'] for g in h['groups']]} for h in m['near_fitting_accessory_hits']]} for m in models]},ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
