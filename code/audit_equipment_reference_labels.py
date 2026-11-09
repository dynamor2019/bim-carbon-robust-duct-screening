"""Decoded IFC label search and common reference inventory; no identity or registration inferred."""
import json
from pathlib import Path
import numpy as np
import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.unit
from trace_source_boundary import simple,group_memberships
from recover_fitting_interfaces import sha

TOKENS=('302PF01','302PK01','307TK01','FUTURE S09')


def strings(value):
    if isinstance(value,str):
        yield value
    elif isinstance(value,(list,tuple)):
        for child in value:
            yield from strings(child)
    elif isinstance(value,ifcopenshell.entity_instance) and value.id()==0:
        yield from strings(value.wrappedValue)


def matches(value):
    texts=[text.upper() for text in strings(value)]
    return [token for token in TOKENS if any(token in text for text in texts)]


def references(source,scale):
    rows=[]
    for kind in ('IfcSite','IfcBuilding','IfcBuildingStorey','IfcGrid'):
        for entity in source.by_type(kind):
            placement=ifcopenshell.util.placement.get_local_placement(entity.ObjectPlacement) if entity.ObjectPlacement else None
            rows.append({'ifc_id':entity.id(),'type':kind,'guid':entity.GlobalId,'name':entity.Name,
                'elevation_m':entity.Elevation*scale if kind=='IfcBuildingStorey' and entity.Elevation is not None else None,
                'placement_rotation':placement[:3,:3].tolist() if placement is not None else None,
                'placement_translation_m':(placement[:3,3]*scale).tolist() if placement is not None else None})
    return rows


def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'milestones/reproducibility'
    inventory_path=root/'architecture-space-inventory.json'
    inventory=json.loads(inventory_path.read_text(encoding='utf-8'))
    sources=[]
    for model in inventory['architectural_models']:
        sources.append((Path(model['source_path']),'architecture',model['source_sha256']))
    for material in ('Concrete','Timber'):
        path=project.parent/'extracted/HVAC/IFC'/f'HVAC_NordicLCA_Office_{material}_BuildingPermit.ifc'
        sources.append((path,'hvac',sha(path)))
    models=[]
    for path,discipline,expected in sources:
        if sha(path)!=expected:
            raise ValueError('Original source changed')
        print('Decoded labels and references:',path.name,flush=True)
        source=ifcopenshell.open(str(path))
        scale=ifcopenshell.util.unit.calculate_unit_scale(source)
        ref=references(source,scale)
        hits=[]
        entity_count=0
        for entity in source:
            entity_count+=1
            for index,value in enumerate(entity):
                tokens=matches(value)
                if tokens:
                    hits.append({'entity_id':entity.id(),'type':entity.is_a(),'attribute':entity.attribute_name(index),
                        'tokens':tokens,'value':simple(value)})
        equipment=[]
        if discipline=='hvac':
            for entity in source.by_type('IfcFan'):
                equipment.append({'ifc_id':entity.id(),'guid':entity.GlobalId,'name':entity.Name,'tag':entity.Tag,
                    'description':entity.Description,'object_type':entity.ObjectType,'predefined_type':entity.PredefinedType,
                    'native_group_memberships':group_memberships(entity),'psets':simple(ifcopenshell.util.element.get_psets(entity))})
        del source
        if sha(path)!=expected:
            raise ValueError('Original changed during decoded search')
        models.append({'source':path.name,'path':str(path),'discipline':discipline,'sha256':expected,'entity_count':entity_count,
            'references':ref,'token_hit_counts':{token:sum(token in h['tokens'] for h in hits) for token in TOKENS},
            'decoded_string_hits':hits,'fans':equipment})
    comparisons=[]
    for hvac in (m for m in models if m['discipline']=='hvac'):
        for arch in (m for m in models if m['discipline']=='architecture' and ('Timber' in m['source'])==('Timber' in hvac['source'])):
            paired=[]
            for a in hvac['references']:
                for b in arch['references']:
                    if a['guid']==b['guid']:
                        paired.append({'guid':a['guid'],'hvac':a,'architecture':b,
                            'translation_gap_m':float(np.linalg.norm(np.array(a['placement_translation_m'])-b['placement_translation_m'])) if a['placement_translation_m'] is not None and b['placement_translation_m'] is not None else None})
            comparisons.append({'hvac':hvac['source'],'architecture':arch['source'],'shared_reference_guid_pairs':paired,
                'status':'SHARED_DECLARATION_ONLY; independent_geometric_anchor_registration_not_certified'})
    report={'artifact_type':'decoded_equipment_labels_and_shared_IFC_reference_objects','status':'IDENTITY_AND_REGISTRATION_UNCERTIFIED',
        'inputHashes':{inventory_path.name:sha(inventory_path)},'source_files':[{'path':str(p),'sha256':s} for p,d,s in sources],
        'codeSha256':sha(Path(__file__)),'models':models,'paired_reference_comparisons':comparisons,
        'limitations':['Exhaustive decoded-string search covers stored primitive string attributes and aggregate simple values, not external documents or unstored identifiers.',
            'Zero label hits cannot certify absence of the physical equipment or hidden/coded designation.',
            'Shared reference GUIDs, placements or storey labels are declarations, not independent cross-discipline geometric registration.',
            'Native system membership is not physical service or fan performance evidence.']}
    (root/'equipment-reference-label-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'models':[{'source':m['source'],'entity_count':m['entity_count'],'token_counts':m['token_hit_counts'],
        'reference_counts':{kind:sum(r['type']==kind for r in m['references']) for kind in ('IfcSite','IfcBuilding','IfcBuildingStorey','IfcGrid')},
        'fans':[{'id':f['ifc_id'],'name':f['name'],'tag':f['tag']} for f in m['fans']]} for m in models],
        'shared_guid_counts':[{'hvac':c['hvac'],'architecture':c['architecture'],'count':len(c['shared_reference_guid_pairs'])} for c in comparisons]},ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
