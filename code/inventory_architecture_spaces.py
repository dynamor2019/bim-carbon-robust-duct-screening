"""Inventory architecture spaces and declared coordinate contexts before spatial joining."""
import json
from pathlib import Path
import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.unit
import fitz
from recover_fitting_interfaces import sha


def context(source):
    scale=ifcopenshell.util.unit.calculate_unit_scale(source)
    contexts=[]
    for item in source.by_type('IfcGeometricRepresentationContext',include_subtypes=False):
        wcs=item.WorldCoordinateSystem
        contexts.append({'id':item.id(),'identifier':item.ContextIdentifier,'type':item.ContextType,
            'world_coordinate_system':wcs.get_info(recursive=True) if wcs else None,
            'true_north':item.TrueNorth.DirectionRatios if item.TrueNorth else None})
    maps=[]
    if source.schema!='IFC2X3':
        maps=[item.get_info(recursive=True) for item in source.by_type('IfcMapConversion')]
    sites=[{'guid':item.GlobalId,'name':item.Name,'latitude':item.RefLatitude,'longitude':item.RefLongitude,
        'elevation_raw':item.RefElevation,'placement_raw':ifcopenshell.util.placement.get_local_placement(item.ObjectPlacement).tolist() if item.ObjectPlacement else None} for item in source.by_type('IfcSite')]
    storeys=[{'guid':item.GlobalId,'name':item.Name,'long_name':item.LongName,'elevation_raw':item.Elevation,
        'elevation_m_candidate':item.Elevation*scale if item.Elevation is not None else None,
        'placement_raw':ifcopenshell.util.placement.get_local_placement(item.ObjectPlacement).tolist() if item.ObjectPlacement else None} for item in source.by_type('IfcBuildingStorey')]
    return {'schema':source.schema,'length_scale_to_m':scale,'contexts':contexts,'map_conversions':maps,'sites':sites,'storeys':storeys}


def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'milestones/reproducibility'
    index_path=root/'architecture-source-index.json'
    index=json.loads(index_path.read_text(encoding='utf-8'))
    if index['status']!='SELECTED_SOURCES_CRC_VERIFIED':
        raise ValueError('Selected architecture downloads not verified')
    models=[]
    documents=[]
    hashes={index_path.name:sha(index_path)}
    for record in index['selected_sources']:
        path=Path(record['path'])
        before=sha(path)
        if before!=record['sha256']:
            raise ValueError('Selected source hash differs')
        if path.suffix.lower()=='.pdf':
            document=fitz.open(path)
            pages=[]
            folder=project/'.dsh-state/architecture-cache/specification-text'/path.stem
            folder.mkdir(parents=True,exist_ok=True)
            for number,page in enumerate(document,1):
                text=folder/f'page{number:02d}.txt'
                text.write_text(page.get_text('text'),encoding='utf-8')
                pages.append({'physical_page':number,'path':str(text),'sha256':sha(text)})
            documents.append({'source_path':str(path),'sha256':before,'pages':pages})
            document.close()
            continue
        if path.suffix.lower()!='.ifc':
            continue
        print('Inventory architecture spaces:',path.name,flush=True)
        source=ifcopenshell.open(str(path))
        spaces=[]
        for space in source.by_type('IfcSpace'):
            parents=[]
            for relation in space.Decomposes:
                parent=relation.RelatingObject
                parents.append({'type':parent.is_a(),'guid':getattr(parent,'GlobalId',None),'name':getattr(parent,'Name',None)})
            spaces.append({'ifc_id':space.id(),'guid':space.GlobalId,'name':space.Name,'long_name':space.LongName,
                'description':space.Description,'parents':parents,'psets':ifcopenshell.util.element.get_psets(space),
                'placement_raw':ifcopenshell.util.placement.get_local_placement(space.ObjectPlacement).tolist() if space.ObjectPlacement else None})
        metadata=context(source)
        del source
        if sha(path)!=before:
            raise ValueError('Architecture source changed during inventory')
        models.append({'source_name':path.name,'source_path':str(path),'source_sha256':before,'coordinate_metadata':metadata,'spaces':spaces})
    hvac=[]
    for material in ['concrete','timber']:
        interface_path=root/'network-interfaces'/(material+'-interfaces.json')
        hashes[interface_path.name]=sha(interface_path)
        interface=json.loads(interface_path.read_text(encoding='utf-8'))
        path=project.parent/'extracted/HVAC/IFC'/(interface['model_id']+'.ifc')
        if sha(path)!=interface['sourceSha256']:
            raise ValueError('HVAC original hash differs')
        print('Inventory HVAC coordinate context:',material,flush=True)
        source=ifcopenshell.open(str(path))
        hvac.append({'model_id':interface['model_id'],'source_sha256':interface['sourceSha256'],'coordinate_metadata':context(source),'space_count':len(source.by_type('IfcSpace'))})
        del source
    report={'artifact_type':'architecture_space_and_coordinate_inventory','status':'COORDINATE_ALIGNMENT_NOT_YET_VERIFIED',
        'inputHashes':hashes,'codeSha256':sha(Path(__file__)),'architectural_models':models,'hvac_models':hvac,'specifications':documents,
        'limitations':['Source names and placements are evidence, not geometric containment certification.',
            'Archicad/Revit exports are alternative representations, not independent buildings.',
            'MapConversion and source unit scales must be checked before cross-discipline joining.']}
    (root/'architecture-space-inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8',newline='')
    keywords=('sauna','pesu','puku','neuvott','toimisto','kunto')
    print(json.dumps({'architecture':[{'name':m['source_name'],'space_count':len(m['spaces']),
        'storeys':m['coordinate_metadata']['storeys'],'functional_label_candidates':[{'id':s['ifc_id'],'name':s['name'],'long_name':s['long_name'],'parents':s['parents']}
            for s in m['spaces'] if any(word in ((s['name'] or '')+' '+(s['long_name'] or '')).lower() for word in keywords)]} for m in models],
        'HVAC':[{'model_id':m['model_id'],'space_count':m['space_count'],'length_scale':m['coordinate_metadata']['length_scale_to_m']} for m in hvac]},ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
