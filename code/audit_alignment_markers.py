"""Search all product labels for explicit alignment markers and extract raw marker geometry."""
import json,re
from pathlib import Path
import numpy as np
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.unit
import ifcopenshell.util.placement
import ifcopenshell.util.element
import fitz
from trace_source_boundary import simple
from recover_fitting_interfaces import sha


def marker_label(entity):
    return any(re.search(r'align|kohdist|survey|shared',str(getattr(entity,key,None) or ''),re.I) for key in ('Name','Description','ObjectType','Tag'))


def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'milestones/reproducibility'
    input_path=root/'equipment-reference-label-audit.json'
    data=json.loads(input_path.read_text(encoding='utf-8'))
    models=[]
    for model in data['models']:
        path=Path(model['path'])
        if sha(path)!=model['sha256']:
            raise ValueError('Source changed')
        print('Explicit marker labels:',path.name,flush=True)
        source=ifcopenshell.open(str(path))
        scale=ifcopenshell.util.unit.calculate_unit_scale(source)
        products=source.by_type('IfcProduct')
        hits=[]
        for entity in products:
            if not marker_label(entity):
                continue
            matrix=ifcopenshell.util.placement.get_local_placement(entity.ObjectPlacement) if entity.ObjectPlacement else None
            geometry=None
            if entity.Representation is not None:
                settings=ifcopenshell.geom.settings()
                settings.set(settings.USE_WORLD_COORDS,True)
                shape=ifcopenshell.geom.create_shape(settings,entity)
                vertices=np.array(shape.geometry.verts).reshape(-1,3)
                if not len(vertices) or not np.isfinite(vertices).all():
                    raise ValueError('Invalid marker mesh')
                geometry={'min_m':vertices.min(axis=0).tolist(),'max_m':vertices.max(axis=0).tolist(),
                    'unique_vertices_m':np.unique(np.round(vertices,8),axis=0).tolist(),
                    'vertex_count':len(vertices),'note':'World mesh coordinates already metres; unique rounding is bookkeeping, not registration fitting.'}
            hits.append({'id':entity.id(),'guid':entity.GlobalId,'type':entity.is_a(),'name':entity.Name,
                'description':entity.Description,'object_type':getattr(entity,'ObjectType',None),'tag':getattr(entity,'Tag',None),
                'placement_translation_m':(matrix[:3,3]*scale).tolist() if matrix is not None else None,
                'placement_rotation':matrix[:3,:3].tolist() if matrix is not None else None,
                'psets':simple(ifcopenshell.util.element.get_psets(entity)),'geometry':geometry})
        del source
        if sha(path)!=model['sha256']:
            raise ValueError('Source changed')
        models.append({'source':model['source'],'discipline':model['discipline'],'sha256':model['sha256'],
            'product_count':len(products),'marker_hits':hits})
    specs=[]
    cache=project/'.dsh-state/source-extracts'
    source_files=[{'path':m['path'],'sha256':m['sha256']} for m in data['models']]
    for material in ('Concrete','Timbere'):
        pdf=project.parent/'extracted/HVAC/SPECIFICATIONS'/f'HVAC_NordicLCA_Office_{material}_BuildingPermit_BIM_Specification.pdf'
        source_files.append({'path':str(pdf),'sha256':sha(pdf)})
        doc=fitz.open(pdf)
        pages=[]
        for i,page in enumerate(doc):
            text=page.get_text('text',sort=True)
            text_path=cache/f'{pdf.stem}_page{i+1:02d}.txt'
            text_path.write_text(text,encoding='utf-8',newline='')
            pages.append({'physical_page':i+1,'text_path':str(text_path),'text_sha256':sha(text_path),
                'alignment_origin_lines':[line for line in text.splitlines() if re.search(r'align|cube|origin|origo|kohdist|kuutio|coordinate',line,re.I)]})
        doc.close()
        if sha(pdf)!=source_files[-1]['sha256']:
            raise ValueError('Specification changed')
        specs.append({'source':pdf.name,'pages':pages})
    report={'artifact_type':'explicit_alignment_marker_labels_geometry_and_HVAC_specification','status':'EXPLICIT_MARKER_DIAGNOSIS_ONLY',
        'inputHashes':{input_path.name:sha(input_path)},'source_files':source_files,'codeSha256':sha(Path(__file__)),
        'models':models,'hvac_specifications':specs,
        'limitations':['Search covers product Name/Description/ObjectType/Tag only, not every hidden property or unlabeled geometrical anchor.',
            'An HVAC-only marker does not independently validate architecture registration or projected map origin.',
            'No coordinate shift, best-fit transform, source repair or service reassignment applied.']}
    (root/'alignment-marker-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'models':[{'source':m['source'],'product_count':m['product_count'],'markers':m['marker_hits']} for m in models],
        'specifications':specs},ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
