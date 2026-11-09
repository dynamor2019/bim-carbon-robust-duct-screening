"""Trace native assignments around rectangular duct fittings and AHU using existing bbox caches.
BBox neighbors are context only, never inserted as physical connections.
"""
import json
import math
import re
from pathlib import Path
import ifcopenshell
from trace_source_boundary import group_memberships
from recover_fitting_interfaces import sha


def gap(a,b):
    values=[max(a['bbox_min_m'][i]-b['bbox_max_m'][i],b['bbox_min_m'][i]-a['bbox_max_m'][i],0) for i in range(3)]
    return math.sqrt(sum(v*v for v in values))


def main():
    project=Path(__file__).resolve().parents[1]
    folder=project/'milestones/reproducibility/network-interfaces'
    reports=[]
    hashes={}
    for material in ['concrete','timber']:
        path=folder/(material+'-interfaces.json')
        hashes[path.name]=sha(path)
        data=json.loads(path.read_text(encoding='utf-8'))
        source_path=project.parent/'extracted/HVAC/IFC'/(data['model_id']+'.ifc')
        before=sha(source_path)
        if before!=data['sourceSha256']:
            raise ValueError('Original IFC changed from cached inventory')
        print('Reading native assignments only:',material,flush=True)
        source=ifcopenshell.open(str(source_path))
        records=[r for r in data['components'] if 'bbox_min_m' in r]
        targets=[r for r in records if r['ifc_type']=='IfcFan' or re.search(r'800[xX×]1400',str(r.get('psets',{}).get('FI_Geometria',{}).get('Liitoskoko (DU)','')))]
        contexts=[]
        for target in targets:
            neighbors=[]
            for other in records:
                if other['ifc_id']==target['ifc_id']:
                    continue
                distance=gap(target,other)
                if distance>.05:
                    continue
                neighbors.append({'ifc_id':other['ifc_id'],'guid':other['guid'],'ifc_type':other['ifc_type'],
                    'name':other['name'],'bbox_gap_m':distance,
                    'source_floor_label':other['psets'].get('FI_Sijainti',{}).get('Kerros'),
                    'source_connection_DU':other['psets'].get('FI_Geometria',{}).get('Liitoskoko (DU)'),
                    'source_raw_flow':other['psets'].get('FI_Tekninen',{}).get('Virtaama'),
                    'native_assignments':group_memberships(source.by_id(other['ifc_id'])),
                    'status':'BBOX_CONTEXT_NOT_PHYSICAL_EDGE'})
            contexts.append({'ifc_id':target['ifc_id'],'guid':target['guid'],'ifc_type':target['ifc_type'],'name':target['name'],
                'native_assignments':group_memberships(source.by_id(target['ifc_id'])),
                'source_property_system':target['psets'].get('FI_Sijainti',{}).get('Järjestelmien nimet'),
                'source_product':target['psets'].get('FI_Tuote',{}),'source_device_id':target['psets'].get('FI_Komponentti',{}).get('Laitetunnus'),
                'bbox_neighbors':sorted(neighbors,key=lambda r:(r['bbox_gap_m'],r['ifc_id']))})
        del source
        after=sha(source_path)
        if before!=after:
            raise ValueError('Original IFC changed during semantic trace')
        reports.append({'model_id':data['model_id'],'source_sha256':before,'source_sha256_after':after,
            'contexts':contexts,'scope':'Native assignments for cached 302 members only; outside-group neighbors not ruled out.'})
    result={'artifact_type':'rectangular_native_assignment_context','status':'REQUIRES_ENGINEERING_REVIEW','inputHashes':hashes,
        'codeSha256':sha(Path(__file__)),'assignmentHelperSha256':sha(Path(__file__).with_name('trace_source_boundary.py')),
        'models':reports,'limitations':['Group membership is not service-direction certification.',
            '50 mm bbox screening is context retrieval, not a port/joint tolerance.']}
    (folder/'rectangular-native-context.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps([{'model_id':r['model_id'],'targets':[{'id':t['ifc_id'],'name':t['name'],
        'groups':[g['group_name'] for g in t['native_assignments']],
        'neighbors':[{'id':n['ifc_id'],'name':n['name'],'gap_m':n['bbox_gap_m'],'raw_flow':n['source_raw_flow'],
            'groups':[g['group_name'] for g in n['native_assignments']]} for n in t['bbox_neighbors']]} for t in r['contexts']]} for r in reports],ensure_ascii=True,indent=2),flush=True)


if __name__=='__main__':
    main()
