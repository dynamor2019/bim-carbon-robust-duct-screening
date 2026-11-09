"""Re-extract selected paired IFC boundary geometry; no native ports invented."""
import csv
import hashlib
import json
from pathlib import Path
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.unit
import numpy as np


def csv_rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def nearest_vertex_distance(a, b):
    """Vertex distance upper bounds surface distance; it is not a port gap."""
    best=float('inf')
    for start in range(0,len(a),128):
        delta=a[start:start+128,None,:]-b[None,:,:]
        best=min(best,float(np.sqrt(np.sum(delta*delta,axis=2).min())))
    return best


def indexed_circle_center(curve):
    # Cyclic rectangle corners do not establish a circular curve. Native arcs
    # must form a closed chain before a source circular radius is assigned.
    segments=getattr(curve,'Segments',None)
    if not segments or not all(s.is_a('IfcArcIndex') for s in segments):
        return None
    chains=[tuple(s.wrappedValue) for s in segments]
    if any(len(s)!=3 for s in chains) or any(chains[i][-1]!=chains[(i+1)%len(chains)][0] for i in range(len(chains))):
        return None
    points=np.array(curve.Points.CoordList,dtype=float)[:,:2]
    if len(points)<3:
        return None
    for index in range(2,len(points)):
        matrix=2*np.array([points[1]-points[0],points[index]-points[0]])
        if abs(np.linalg.det(matrix))<1e-12:
            continue
        rhs=np.array([np.dot(points[1],points[1])-np.dot(points[0],points[0]),
                      np.dot(points[index],points[index])-np.dot(points[0],points[0])])
        center=np.linalg.solve(matrix,rhs)
        radius=np.linalg.norm(points-center,axis=1)
        if radius.min()>0 and np.ptp(radius)<=max(1e-6,radius.mean()*1e-6):
            return center
        return None
    return None


def indexed_polygon_points(curve):
    segments=getattr(curve,'Segments',None)
    coords=np.array(curve.Points.CoordList,dtype=float)[:,:2]
    if not segments:
        return coords
    if not all(s.is_a('IfcLineIndex') for s in segments):
        return None
    indices=[]
    for segment in segments:
        current=list(segment.wrappedValue)
        if len(current)<2 or (indices and indices[-1]!=current[0]):
            return None
        indices.extend(current if not indices else current[1:])
    if not indices or min(indices)<1 or max(indices)>len(coords):
        return None
    return coords[np.array(indices,dtype=int)-1]


def polygon_center(points):
    if points is None or len(points)<4 or not np.allclose(points[0],points[-1],atol=1e-8,rtol=0):
        return None
    x,y=points[:-1,0],points[:-1,1]
    xn,yn=points[1:,0],points[1:,1]
    cross=x*yn-xn*y
    signed_twice_area=cross.sum()
    if abs(signed_twice_area)<1e-12:
        return None
    return np.array([np.sum((x+xn)*cross)/(3*signed_twice_area),
                     np.sum((y+yn)*cross)/(3*signed_twice_area)])


def extrusion_axes(entity, unit_scale):
    """Recover source extrusion axes; distinguish circular arcs from polygons."""
    axes=[]
    object_matrix=ifcopenshell.util.placement.get_local_placement(entity.ObjectPlacement)
    def visit(item, parent):
        if item.is_a('IfcMappedItem'):
            transform=ifcopenshell.util.placement.get_mappeditem_transformation(item)
            for child in item.MappingSource.MappedRepresentation.Items:
                visit(child, parent @ transform)
        elif item.is_a('IfcExtrudedAreaSolid'):
            profile=item.SweptArea
            profile_position=getattr(profile,'Position',None)
            center=np.array([0.,0.,0.,1.])
            method='circle_profile_origin'
            radius_raw=getattr(profile,'Radius',None)
            if not profile.is_a('IfcCircleProfileDef'):
                outer=getattr(profile,'OuterCurve',None)
                if not outer:
                    return
                if outer.is_a('IfcIndexedPolyCurve'):
                    fitted=indexed_circle_center(outer)
                    if fitted is not None:
                        center[:2]=fitted
                        method='closed_native_indexed_arcs_share_circle_center; outer_profile_only'
                        radius_raw=float(np.mean(np.linalg.norm(np.array(outer.Points.CoordList,dtype=float)[:,:2]-fitted,axis=1)))
                    else:
                        fitted=polygon_center(indexed_polygon_points(outer))
                        if fitted is None:
                            return
                        center[:2]=fitted
                        method='indexed_outer_closed_polygon_area_centroid; no_circular_radius'
                        radius_raw=None
                elif outer.is_a('IfcPolyline'):
                    points=np.array([p.Coordinates[:2] for p in outer.Points],dtype=float)
                    if len(points)<4 or not np.allclose(points[0],points[-1],atol=1e-8):
                        return
                    x,y=points[:-1,0],points[:-1,1]
                    xn,yn=points[1:,0],points[1:,1]
                    cross=x*yn-xn*y
                    signed_twice_area=cross.sum()
                    if abs(signed_twice_area)<1e-12:
                        return
                    center[:2]=[np.sum((x+xn)*cross)/(3*signed_twice_area),
                                np.sum((y+yn)*cross)/(3*signed_twice_area)]
                    method='outer_closed_polygon_area_centroid; voids_not_used'
                else:
                    return
            solid_matrix=ifcopenshell.util.placement.get_axis2placement(item.Position) if item.Position else np.eye(4)
            profile_matrix=ifcopenshell.util.placement.get_axis2placement(profile_position) if profile_position else np.eye(4)
            start=profile_matrix @ center
            direction=np.array(item.ExtrudedDirection.DirectionRatios,dtype=float)
            direction=direction / np.linalg.norm(direction)
            end=start.copy()
            end[:3]+=direction * item.Depth
            matrix=parent @ solid_matrix
            world_a=(matrix @ start)[:3]*unit_scale
            world_b=(matrix @ end)[:3]*unit_scale
            scales=np.linalg.svd(matrix[:3,:3],compute_uv=False)
            radius_m=radius_raw*float(scales.mean())*unit_scale if radius_raw and np.ptp(scales)<1e-8 else None
            axes.append({'solid_ifc_id':item.id(), 'profile_type':profile.is_a(), 'source_outer_radius_m':radius_m,
                'end_a_m':world_a.tolist(),'end_b_m':world_b.tolist(),
                'axis_length_m':float(np.linalg.norm(world_b-world_a)),
                'depth_raw_ifc_units':item.Depth, 'profile_radius_raw_ifc_units':getattr(profile,'Radius',None),
                'profile_center_method':method,
                'evidence_limit':'Axis through source extrusion profile center; not a native port or service assignment.'})
    for representation in entity.Representation.Representations:
        if representation.RepresentationIdentifier=='Body':
            for item in representation.Items:
                visit(item,object_matrix)
    return axes


def shape_record(entity, settings, unit_scale, mesh_cache=None):
    shape=ifcopenshell.geom.create_shape(settings,entity)
    vertices=np.asarray(shape.geometry.verts,dtype=float).reshape(-1,3)
    if not len(vertices) or not np.isfinite(vertices).all():
        raise ValueError('empty/nonfinite geometry')
    mean=vertices.mean(axis=0)
    result={'bbox_min_m':vertices.min(axis=0).tolist(), 'bbox_max_m':vertices.max(axis=0).tolist(),
            'vertex_mean_m':mean.tolist(), 'vertex_count':len(vertices),
            'ifc_id':entity.id(),'guid':entity.GlobalId,'name':entity.Name,'ifc_type':entity.is_a(),
            'psets':ifcopenshell.util.element.get_psets(entity),
            'local_placement_matrix_raw_ifc_units':ifcopenshell.util.placement.get_local_placement(entity.ObjectPlacement).tolist(),
            'representations':[], 'evidence_limit':'Recomputed world-coordinate mesh; no native connector or direction certification.'}
    if mesh_cache:
        faces=np.asarray(shape.geometry.faces,dtype=np.int64).reshape(-1,3)
        mesh_cache.parent.mkdir(parents=True,exist_ok=True)
        np.savez_compressed(mesh_cache,vertices=vertices,faces=faces)
        result['mesh_cache']={'path':str(mesh_cache),'sha256':sha(mesh_cache),'triangle_count':len(faces),
                              'coordinate_system':'IFC world coordinates in m; no additional placement'}
    for representation in entity.Representation.Representations:
        items=[]
        for item in representation.Items:
            record={'ifc_id':item.id(),'ifc_type':item.is_a()}
            if item.is_a('IfcMappedItem'):
                mapped=item.MappingSource.MappedRepresentation
                record['mapped_items']=[{'ifc_id':x.id(),'ifc_type':x.is_a(),
                    'profile_type': x.SweptArea.is_a() if x.is_a('IfcExtrudedAreaSolid') else None,
                    'outer_curve_type': getattr(x.SweptArea,'OuterCurve',None).is_a()
                       if x.is_a('IfcExtrudedAreaSolid') and getattr(x.SweptArea,'OuterCurve',None) else None}
                    for x in mapped.Items]
            items.append(record)
        result['representations'].append({'identifier':representation.RepresentationIdentifier,
                                          'type':representation.RepresentationType,'items':items})
    if entity.is_a('IfcDuctSegment'):
        result['profile_extrusion_axes']=extrusion_axes(entity,unit_scale)
        for axis in result['profile_extrusion_axes']:
            ends=np.array([axis['end_a_m'],axis['end_b_m']])
            outside=np.maximum(np.maximum(vertices.min(axis=0)-ends,ends-vertices.max(axis=0)),0.)
            axis['mesh_bbox_endpoint_outside_max_m']=float(np.max(outside))
            if np.max(outside)>1e-6:
                raise ValueError('Extrusion endpoints do not fit world mesh bbox; transformation must be reviewed')
        result['extrusion_axis_extraction_status']='EXTRACTED_GEOMETRIC_AXES_ONLY' if result['profile_extrusion_axes'] else 'UNSUPPORTED_PROFILE_NO_AXIS_EXTRACTED'
        result['pca_rejection_note']='PCA longest axis is not a reliable duct axis for short/wide segments; original swept-solid transforms used instead.'
    return result,vertices


def main():
    project=Path(__file__).resolve().parents[1]
    root=project.parent
    pilot_path=root/'research_data/pilot_components_enriched.csv'
    contacts_path=root/'research_data/pilot_inferred_contacts.csv'
    pilot=csv_rows(pilot_path)
    contacts=csv_rows(contacts_path)
    timber='HVAC_NordicLCA_Office_Timber_BuildingPermit'
    concrete='HVAC_NordicLCA_Office_Concrete_BuildingPermit'
    timber_ids=['3137757','3137836','3909314','3137622']
    selected_t=[r for r in pilot if r['model_id']==timber and r['ifc_id'] in timber_ids]
    guids={r['ifc_guid'] for r in selected_t}
    selected_c=[r for r in pilot if r['model_id']==concrete and (r['ifc_guid'] in guids or r['ifc_id']=='3139835')]
    # 3139835 is selected by the explicit 5mm candidate path, not same-GUID matching.
    sources={pilot_path.name:sha(pilot_path), contacts_path.name:sha(contacts_path)}
    result={'artifact_type':'paired_boundary_geometry_review', 'status':'REQUIRES_REVIEW',
            'sourceHashes':sources,'codeSha256':sha(Path(__file__)), 'ifcopenshell_version':ifcopenshell.version,
            'models':[],'paired_geometry':[]}
    all_records={}
    for model, selected in [(concrete,selected_c),(timber,selected_t)]:
        path=root/'extracted/HVAC/IFC'/(model+'.ifc')
        sources[model]=sha(path)
        print('Recomputing selected boundary:',model,flush=True)
        source=ifcopenshell.open(str(path))
        settings=ifcopenshell.geom.settings()
        settings.set(settings.USE_WORLD_COORDS,True)
        records,meshes={},{}
        for row in selected:
            mesh_cache=project/'.dsh-state/boundary-mesh-cache'/model/(row['ifc_id']+'.npz')
            record,mesh=shape_record(source.by_id(int(row['ifc_id'])),settings,ifcopenshell.util.unit.calculate_unit_scale(source),mesh_cache)
            record['pilot_nominal_diameter_m']=float(row['diameter_m']) if row['diameter_m'] else None
            old_min=np.array([float(row[f'bbox_min_{a}_m']) for a in 'xyz'])
            old_max=np.array([float(row[f'bbox_max_{a}_m']) for a in 'xyz'])
            record['pilot_bbox_max_abs_error_m']=float(max(np.max(abs(mesh.min(axis=0)-old_min)),np.max(abs(mesh.max(axis=0)-old_max))))
            records[row['ifc_id']], meshes[row['ifc_id']]=record,mesh
            all_records[(model,row['ifc_guid'])]=record
        pairs=[]
        ids=sorted(records)
        for i,a in enumerate(ids):
            for b in ids[i+1:]:
                ma,mb=meshes[a],meshes[b]
                gap=np.maximum(np.maximum(ma.min(axis=0)-mb.max(axis=0),mb.min(axis=0)-ma.max(axis=0)),0)
                pairs.append({'a':a,'b':b,'bbox_gap_m':float(np.linalg.norm(gap)),
                    'minimum_extrusion_endpoint_gap_m':min((float(np.linalg.norm(np.array(ax1[e1])-np.array(ax2[e2])))
                        for ax1 in records[a].get('profile_extrusion_axes',[]) for ax2 in records[b].get('profile_extrusion_axes',[])
                        for e1 in ['end_a_m','end_b_m'] for e2 in ['end_a_m','end_b_m']), default=None),
                    'nearest_vertex_distance_m':nearest_vertex_distance(ma,mb),
                    'recorded_contacts':[{'tolerance_m':r['tolerance_m'],'basis':r['basis'],'distance_m':r['distance_m']}
                       for r in contacts if r['model_id']==model and {r['component_a'],r['component_b']}=={a,b}],
                    'note':'Vertex minimum is an upper bound on mesh-surface minimum; none of these distances certifies a port.'})
        neighbors=[]
        for r in contacts:
            if r['model_id']==model and float(r['tolerance_m'])==.005 and (r['component_a'] in records or r['component_b'] in records):
                neighbors.append(r)
        result['models'].append({'model_id':model,'selected_entities':list(records.values()),
                                  'selected_pair_distances':pairs,'candidate_5mm_neighbors':neighbors})
        del source
    for guid in sorted(guids):
        if (concrete,guid) in all_records and (timber,guid) in all_records:
            a,b=all_records[(concrete,guid)],all_records[(timber,guid)]
            result['paired_geometry'].append({'guid':guid,'concrete_id':a['ifc_id'],'timber_id':b['ifc_id'],
                 'bbox_min_shift_m':(np.array(b['bbox_min_m'])-np.array(a['bbox_min_m'])).tolist(),
                 'bbox_max_shift_m':(np.array(b['bbox_max_m'])-np.array(a['bbox_max_m'])).tolist(),
                 'note':'Same GUID indicates a paired design entity, not unchanged geometry or independent samples.'})
    out=project/'milestones/reproducibility/boundary-evidence/paired-boundary-geometry.json'
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'pairs':[{'model':m['model_id'],'distances':m['selected_pair_distances']} for m in result['models']],
                      'paired_geometry':result['paired_geometry']},ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
