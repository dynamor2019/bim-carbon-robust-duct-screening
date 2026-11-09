"""Audit native indexed-curve segment types against cached profile classification."""
import json
from pathlib import Path
import ifcopenshell
from recover_fitting_interfaces import sha


def solids(item):
    if item.is_a('IfcMappedItem'):
        for child in item.MappingSource.MappedRepresentation.Items:
            yield from solids(child)
    elif item.is_a('IfcExtrudedAreaSolid'):
        yield item


def main():
    project=Path(__file__).resolve().parents[1]
    folder=project/'milestones/reproducibility/network-interfaces'
    reports=[]
    for material in ['concrete','timber']:
        path=folder/(material+'-interfaces.json')
        data=json.loads(path.read_text(encoding='utf-8'))
        source_path=project.parent/'extracted/HVAC/IFC'/(data['model_id']+'.ifc')
        if sha(source_path)!=data['sourceSha256']:
            raise ValueError('Source hash mismatch')
        source=ifcopenshell.open(str(source_path))
        rows=[]
        for record in data['components']:
            if record['ifc_type']!='IfcDuctSegment':
                continue
            entity=source.by_id(record['ifc_id'])
            native=[]
            for representation in entity.Representation.Representations:
                if representation.RepresentationIdentifier!='Body':
                    continue
                for item in representation.Items:
                    for solid in solids(item):
                        outer=getattr(solid.SweptArea,'OuterCurve',None)
                        if outer and outer.is_a('IfcIndexedPolyCurve'):
                            segments=list(outer.Segments or ())
                            native.append({'solid_ifc_id':solid.id(),'curve_ifc_id':outer.id(),
                                'point_count':len(outer.Points.CoordList),'segment_types':[s.is_a() for s in segments],
                                'segments_raw':[str(s) for s in segments],
                                'declared_circular_arcs':bool(segments) and all(s.is_a('IfcArcIndex') for s in segments)})
            axis_by_solid={a['solid_ifc_id']:a for a in record.get('axes',[])}
            for curve in native:
                axis=axis_by_solid.get(curve['solid_ifc_id'])
                if axis and axis.get('source_outer_radius_m') is not None and not curve['declared_circular_arcs']:
                    rows.append({'ifc_id':record['ifc_id'],'guid':record['guid'],'name':record['name'],
                        'source_geometry':record['psets'].get('FI_Geometria',{}),'native_curve':curve,
                        'cached_axis':axis,'status':'FAIL_NATIVE_PROFILE_ROLE; cyclic_points_do_not_prove_circle'})
        entity=None
        del source
        reports.append({'model_id':data['model_id'],'inventory_sha256':sha(path),'source_sha256':data['sourceSha256'],
            'failed_profile_roles':rows,'failure_count':len(rows)})
    result={'artifact_type':'native_profile_role_validation','status':'FAIL' if any(r['failure_count'] for r in reports) else 'PASS',
        'codeSha256':sha(Path(__file__)),'models':reports,'limitation':'All-arc evidence alone does not certify native ports or flow direction.'}
    (folder/'profile-type-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps(result,ensure_ascii=True,indent=2),flush=True)
    if result['status']=='FAIL':
        raise SystemExit(2)


if __name__=='__main__':
    main()
