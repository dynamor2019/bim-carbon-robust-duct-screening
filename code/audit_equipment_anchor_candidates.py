"""Inventory possible common physical objects and retain multi-system AHU designations."""
import json
from pathlib import Path
from collections import Counter
import ifcopenshell
import ifcopenshell.util.element
from trace_source_boundary import bbox,group_memberships,simple
from recover_fitting_interfaces import sha


def relevant(groups):
    return any('302PK01' in (g.get('group_name') or '') for g in groups)


def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'milestones/reproducibility'
    labels_path=root/'equipment-reference-label-audit.json'
    labels=json.loads(labels_path.read_text(encoding='utf-8'))
    models=[]
    for model in labels['models']:
        path=Path(model['path'])
        if sha(path)!=model['sha256']:
            raise ValueError('Original source changed')
        print('Physical anchor and AHU candidates:',path.name,flush=True)
        source=ifcopenshell.open(str(path))
        elements=source.by_type('IfcBuildingElement')
        counts=dict(Counter(e.is_a() for e in elements))
        anchors=[{'ifc_id':e.id(),'type':e.is_a(),'guid':e.GlobalId,'name':e.Name,'tag':getattr(e,'Tag',None)} for e in elements]
        equipment=[]
        if model['discipline']=='hvac':
            for entity in source.by_type('IfcFan'):
                groups=group_memberships(entity)
                if not relevant(groups):
                    continue
                psets=simple(ifcopenshell.util.element.get_psets(entity))
                equipment.append({'ifc_id':entity.id(),'guid':entity.GlobalId,'name':entity.Name,'tag':entity.Tag,
                    'description':entity.Description,'groups':groups,'psets':psets,'world_mesh_bbox':bbox(entity),
                    'declared_device_code':psets.get('FI_Komponentti',{}).get('Laitetunnus'),
                    'declared_manufacturer':psets.get('FI_Tuote',{}).get('Tuotetyypin valmistaja')})
        del source
        if sha(path)!=model['sha256']:
            raise ValueError('Source changed during inspection')
        models.append({'source':model['source'],'discipline':model['discipline'],'source_sha256':model['sha256'],
            'building_element_counts':counts,'building_element_candidates':anchors,'scoped_equipment':equipment})
    paired=[]
    for hvac in (m for m in models if m['discipline']=='hvac'):
        hvac_ids={r['guid']:r for r in hvac['building_element_candidates']}
        for arch in (m for m in models if m['discipline']=='architecture' and ('Timber' in m['source'])==('Timber' in hvac['source'])):
            arch_ids={r['guid']:r for r in arch['building_element_candidates']}
            common=sorted(hvac_ids.keys()&arch_ids.keys())
            paired.append({'hvac':hvac['source'],'architecture':arch['source'],
                'common_building_element_guids':[{'guid':g,'hvac':hvac_ids[g],'architecture':arch_ids[g]} for g in common],
                'status':'GUID_CANDIDATES_ONLY; independent_geometric_registration_not_tested'})
    result={'artifact_type':'common_physical_anchor_candidates_and_scoped_AHU_identity','status':'ANCHOR_AND_DEVICE_IDENTITY_CANDIDATES_ONLY',
        'inputHashes':{labels_path.name:sha(labels_path)},'source_files':[{'path':m['path'],'sha256':m['sha256']} for m in labels['models']],
        'codeSha256':sha(Path(__file__)),'models':models,'paired_physical_anchor_candidates':paired,
        'limitations':['BuildingElement class scope may miss proxies or differently classified anchor objects; absence is not proof that models cannot register.',
            'All original native group assignments retained; IfcFan class and multi-system membership do not identify a single exhaust fan.',
            'BBox location and declared manufacturer/code are not performance or physical connection evidence.',
            'No distance fit, coordinate shift or device-code reassignment performed.']}
    (root/'equipment-anchor-candidate-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'models':[{'source':m['source'],'building_element_counts':m['building_element_counts'],
        'equipment':[{'id':e['ifc_id'],'name':e['name'],'description':e['description'],'declared_device_code':e['declared_device_code'],
            'manufacturer':e['declared_manufacturer'],'groups':[g['group_name'] for g in e['groups']],'bbox':e['world_mesh_bbox']} for e in m['scoped_equipment']]} for m in models],
        'paired_anchor_counts':[{'hvac':p['hvac'],'architecture':p['architecture'],'count':len(p['common_building_element_guids'])} for p in paired]},ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
