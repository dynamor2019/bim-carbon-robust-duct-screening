"""Read original IFC property value types and explicit units without inferring missing units."""
import json
from collections import Counter
from pathlib import Path
import ifcopenshell
from recover_fitting_interfaces import sha
from resolve_ifc_units import resolve_property


def unit_info(unit):
    return unit.get_info(recursive=True) if unit is not None else None


def main():
    project=Path(__file__).resolve().parents[1]
    folder=project/'milestones/reproducibility/network-interfaces'
    hashes={}
    models=[]
    for material in ['concrete','timber']:
        path=folder/(material+'-interfaces.json')
        hashes[path.name]=sha(path)
        data=json.loads(path.read_text(encoding='utf-8'))
        source_path=project.parent/'extracted/HVAC/IFC'/(data['model_id']+'.ifc')
        before=sha(source_path)
        if before!=data['sourceSha256']:
            raise ValueError('Original IFC hash differs')
        print('Read native property units:',material,flush=True)
        source=ifcopenshell.open(str(source_path))
        projects=[{'id':p.id(),'units':unit_info(p.UnitsInContext)} for p in source.by_type('IfcProject')]
        rows=[]
        for record in data['components']:
            if record['ifc_type'] not in ('IfcDuctSegment','IfcAirTerminal'):
                continue
            entity=source.by_id(record['ifc_id'])
            properties={}
            for relation in entity.IsDefinedBy:
                if not relation.is_a('IfcRelDefinesByProperties'):
                    continue
                pset=relation.RelatingPropertyDefinition
                if not pset.is_a('IfcPropertySet') or pset.Name!='FI_Tekninen':
                    continue
                for prop in pset.HasProperties:
                    if prop.is_a('IfcPropertySingleValue') and prop.Name in ('Virtaama','Virtausnopeus'):
                        value=prop.NominalValue
                        properties[prop.Name]={'property_id':prop.id(),'pset_id':pset.id(),'nominal_value_type':value.is_a() if value else None,
                            'raw_value':value.wrappedValue if value else None,'explicit_unit':unit_info(prop.Unit)}
            if len(projects)!=1:
                raise ValueError('Project unit context is not unique')
            for property_record in properties.values():
                property_record['resolved_unit']=resolve_property(property_record,projects[0]['units']['Units'])
            rows.append({'ifc_id':record['ifc_id'],'guid':record['guid'],'ifc_type':record['ifc_type'],'properties':properties})
        summary={}
        for key in ['Virtaama','Virtausnopeus']:
            present=[r['properties'][key] for r in rows if key in r['properties']]
            summary[key]={'present':len(present),'absent':len(rows)-len(present),
                'value_types':dict(Counter(p['nominal_value_type'] for p in present)),
                'explicit_unit_null':sum(p['explicit_unit'] is None for p in present),
                'explicit_unit_present':sum(p['explicit_unit'] is not None for p in present),
                'resolved_scale_counts':dict(Counter(str(p['resolved_unit']['scale_to_SI']) if p['resolved_unit'] else 'UNRESOLVED' for p in present))}
        entity=None
        value=None
        prop=None
        pset=None
        relation=None
        del source
        after=sha(source_path)
        if before!=after:
            raise ValueError('Original IFC changed during unit audit')
        terminals=[r for r in rows if r['ifc_type']=='IfcAirTerminal']
        terminal_quantities=[r['properties'].get('Virtaama') for r in terminals]
        raw_sum=sum(p['raw_value'] for p in terminal_quantities) if terminal_quantities and all(p and isinstance(p['raw_value'],(int,float)) for p in terminal_quantities) else None
        si_sum=sum(p['raw_value']*p['resolved_unit']['scale_to_SI'] for p in terminal_quantities) if raw_sum is not None and all(p['resolved_unit'] for p in terminal_quantities) else None
        models.append({'model_id':data['model_id'],'source_sha256':before,'source_sha256_after':after,
            'project_unit_assignments':projects,'summary':summary,'rows':rows,
            'terminal_source_flow_sum_raw':raw_sum,'terminal_source_flow_sum_m3_s':si_sum})
    result={'artifact_type':'native_IFC_custom_property_unit_audit','status':'SOURCE_UNIT_METADATA_AUDITED',
        'inputHashes':hashes,'codeSha256':sha(Path(__file__)),'unitHelperSha256':sha(Path(__file__).with_name('resolve_ifc_units.py')),
        'models':models,
        'unit_inheritance_reference':'https://raw.githubusercontent.com/buildingSMART/IFC4.3.x-development/master/docs/schemas/resource/IfcPropertyResource/Entities/IfcPropertySingleValue.md',
        'limitations':['Typed measure properties inherit the matching project unit when no property override exists.',
            'Unresolved IfcReal values remain unresolved; no unit inferred from a property name alone.',
            'Unit resolution does not certify simultaneous demand, flow direction or actual measured operating conditions.',
            'No raw value or quantity type rewritten.']}
    result['status']='PASS_TYPED_UNIT_RESOLUTION' if all('Virtaama' in row['properties'] and (row['ifc_type']!='IfcDuctSegment' or 'Virtausnopeus' in row['properties']) and all(p.get('resolved_unit') for p in row['properties'].values()) for model in models for row in model['rows']) else 'REQUIRES_UNIT_REVIEW'
    (folder/'native-property-unit-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8',newline='')
    print(json.dumps([{'model_id':m['model_id'],'summary':m['summary'],'terminal_source_flow_sum_m3_s':m['terminal_source_flow_sum_m3_s'],
        'project_unit_type_names':[u.get('UnitType') for u in m['project_unit_assignments'][0]['units']['Units']]} for m in models],indent=2,default=str),flush=True)


if __name__=='__main__':
    main()
