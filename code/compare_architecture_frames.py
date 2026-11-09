"""Summarize declared coordinate frames and upper-storey space names without assigning service."""
import json
from pathlib import Path
from recover_fitting_interfaces import sha


def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'milestones/reproducibility'
    path=root/'architecture-space-inventory.json'
    data=json.loads(path.read_text(encoding='utf-8'))
    summaries=[]
    for model in data['architectural_models']:
        metadata=model['coordinate_metadata']
        upper=[space for space in model['spaces'] if any(parent['name']=='Level_05' for parent in space['parents'])]
        summaries.append({'source':model['source_name'],'length_scale':metadata['length_scale_to_m'],
            'contexts':metadata['contexts'],'maps':metadata['map_conversions'],'sites':metadata['sites'],
            'storey_elevations':[{'name':s['name'],'elevation_m':s['elevation_m_candidate']} for s in metadata['storeys']],
            'space_count':len(model['spaces']),'level05_spaces':[{'id':s['ifc_id'],'name':s['name'],'long_name':s['long_name'],
                'placement_translation_m':[s['placement_raw'][i][3]*metadata['length_scale_to_m'] for i in range(3)] if s['placement_raw'] else None} for s in upper]})
    hvac=[{'model_id':m['model_id'],'metadata':m['coordinate_metadata']} for m in data['hvac_models']]
    report={'artifact_type':'declared_architecture_HVAC_frame_comparison','status':'DECLARED_CONTEXT_ONLY',
        'inputHashes':{path.name:sha(path)},'codeSha256':sha(Path(__file__)),'architecture':summaries,'hvac':hvac,
        'limitations':['Storey names are not matched by numeric labels automatically.',
            'Declared frame similarity alone is not room containment or fan service certification.']}
    (root/'architecture-frame-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    def brief(metadata):
        return {'scale':metadata['length_scale_to_m'],'maps':[{'target':m['TargetCRS']['Name'],'unit':m['TargetCRS'].get('MapUnit'),
            **{k:m.get(k) for k in ('Eastings','Northings','OrthogonalHeight','XAxisAbscissa','XAxisOrdinate','Scale')}} for m in metadata['map_conversions']]}
    print(json.dumps({'architecture':[{'source':m['source'],'scale':m['length_scale'],'maps':[{'target':c['TargetCRS']['Name'],
        'unit':c['TargetCRS'].get('MapUnit'),**{k:c.get(k) for k in ('Eastings','Northings','OrthogonalHeight','XAxisAbscissa','XAxisOrdinate','Scale')}} for c in m['maps']],
        'level05_spaces':m['level05_spaces']} for m in summaries],'hvac':[{'model_id':m['model_id'],**brief(m['metadata'])} for m in hvac]},ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
