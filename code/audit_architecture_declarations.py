"""Compare primary architectural specification declarations and raw polygon face boundaries."""
import json
import re
from pathlib import Path
import ifcopenshell
from native_polygon_audit import polygon_boundary_incidence
from recover_fitting_interfaces import sha


def declaration(text):
    origin=re.search(r'Origin\s+([\d.]+)\s+([\d.]+)\s+([\d,]+)',text)
    level=re.search(r'Level_05\s+\+([\d,]+)',text)
    return {'origin':[float(v.replace(',','.')) for v in origin.groups()] if origin else None,
        'level05_m':float(level.group(1).replace(',','.')) if level else None,
        'true_north_statement_present':'Models are not rotated in the project coordinate system' in text}


def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'milestones/reproducibility'
    inventory_path=root/'architecture-space-inventory.json'
    spatial_path=root/'upper-floor-spatial-review.json'
    inventory=json.loads(inventory_path.read_text(encoding='utf-8'))
    spatial=json.loads(spatial_path.read_text(encoding='utf-8'))
    sources=[]
    models=[]
    specs={Path(item['source_path']).stem:item for item in inventory['specifications']}
    for model in inventory['architectural_models']:
        name=model['source_name']
        suffix='_Archicad' if '_Archicad' in name else ''
        base=name.removesuffix('.ifc').removesuffix('_Archicad').removesuffix('_Revit')
        spec=specs['BIM_Specification_'+base+suffix]
        page_text=[]
        locations=[]
        for page in spec['pages']:
            path=Path(page['path'])
            if sha(path)!=page['sha256']:
                raise ValueError('Extracted source page changed')
            page_text.append(path.read_text(encoding='utf-8'))
            locations.append({'physical_page':page['physical_page'],'path':str(path),'sha256':page['sha256']})
            sources.append({'path':str(path),'sha256':page['sha256']})
        declared=declaration('\n'.join(page_text))
        metadata=model['coordinate_metadata']
        actual=[s['elevation_m_candidate'] for s in metadata['storeys'] if s['name']=='Level_05']
        maps=[]
        for conversion in metadata['map_conversions']:
            maps.append({'target_name':conversion['TargetCRS']['Name'],'easting':conversion['Eastings'],'northing':conversion['Northings'],
                'orthogonal_height':conversion['OrthogonalHeight'],'scale':conversion['Scale'],
                'difference_from_specification_origin_raw':[conversion[key]-declared['origin'][i] for i,key in enumerate(['Eastings','Northings','OrthogonalHeight'])] if declared['origin'] else None})
        path=Path(model['source_path'])
        if sha(path)!=model['source_sha256']:
            raise ValueError('Original architecture hash differs')
        print('Native polygon audit:',name,flush=True)
        source=ifcopenshell.open(str(path))
        selected=next(m for m in spatial['models'] if m['architecture_source']==name)
        spaces=[]
        for space in selected['space_geometry']:
            if space['name'] not in ('5202','5203','5205'):
                continue
            entity=source.by_id(space['ifc_id'])
            items=[]
            for representation in entity.Representation.Representations:
                if representation.RepresentationIdentifier!='Body':
                    continue
                for item in representation.Items:
                    if not item.is_a('IfcPolygonalFaceSet'):
                        items.append({'type':item.is_a(),'status':'UNSUPPORTED_NATIVE_LOOP_TYPE'})
                        continue
                    loops=[]
                    holes=0
                    for face in item.Faces:
                        loops.append(list(face.CoordIndex))
                        if face.is_a('IfcIndexedPolygonalFaceWithVoids'):
                            for hole in face.InnerCoordIndices:
                                holes+=1
                                loops.append(list(hole))
                    pnindex=item.PnIndex
                    audit=polygon_boundary_incidence(loops) if pnindex is None else {'status':'PNINDEX_MAPPING_NOT_ASSUMED'}
                    items.append({'item_id':item.id(),'type':item.is_a(),'declared_closed':item.Closed,'pnindex':pnindex,
                        'coordinate_count':len(item.Coordinates.CoordList),'face_count':len(item.Faces),'inner_loop_count':holes,
                        'native_boundary_incidence':audit})
            spaces.append({'ifc_id':space['ifc_id'],'name':space['name'],'long_name':space['long_name'],'body_items':items})
        del source
        if sha(path)!=model['source_sha256']:
            raise ValueError('Original architecture changed during audit')
        models.append({'source':name,'source_sha256':model['source_sha256'],'specification_pdf':spec['source_path'],
            'specification_pdf_sha256':spec['sha256'],'source_pages':locations,'specification_declarations':declared,
            'actual_level05_elevations_m':actual,'level05_difference_m':[v-declared['level05_m'] for v in actual] if declared['level05_m'] is not None else None,
            'map_declarations':maps,'native_spaces':spaces})
    report={'artifact_type':'architectural_specification_and_native_polygon_audit','status':'DECLARATION_AND_NATIVE_BOUNDARY_REVIEW_REQUIRED',
        'inputHashes':{inventory_path.name:sha(inventory_path),spatial_path.name:sha(spatial_path)},'source_files':sources,
        'codeSha256':sha(Path(__file__)),'polygonHelperSha256':sha(Path(__file__).with_name('native_polygon_audit.py')),
        'models':models,'limitations':['A source Closed flag is a declaration, not certification that indexed loops form a closed solid.',
            'Direct coordinate indices may include duplicated coordinates; no geometric welding performed in native loop audit.',
            'Map/spec differences are raw declared values; no inferred global registration or correction applied.',
            'No source space definition or mounting-height rule inferred from generic common-property listings.']}
    (root/'architecture-declaration-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps(models,ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
