"""Audit every source exhaust terminal without filtering demand to fit equipment totals."""
import json
import math
from collections import defaultdict
from pathlib import Path
import ifcopenshell
from trace_source_boundary import group_memberships
from recover_fitting_interfaces import sha


def product_family(name):
    if name.startswith('URH/'):
        return 'URH'
    if name.startswith('AHD-') and '+PRL/' in name:
        return 'AHD_PRL'
    return 'OTHER_SOURCE_PRODUCT'


def aggregate(rows,key):
    groups=defaultdict(list)
    for row in rows:
        groups[row[key]].append(row)
    result=[]
    for label,items in sorted(groups.items(),key=lambda item:str(item[0])):
        valid=[r['flow_m3_s'] for r in items if r['flow_m3_s'] is not None]
        result.append({'label':label,'count':len(items),'valid_flow_count':len(valid),
            'flow_sum_m3_s':math.fsum(valid) if len(valid)==len(items) else None})
    return result


def main():
    project=Path(__file__).resolve().parents[1]
    folder=project/'milestones/reproducibility/network-interfaces'
    unit_path=folder/'native-property-unit-review.json'
    unit_data=json.loads(unit_path.read_text(encoding='utf-8'))
    if unit_data['status']!='PASS_TYPED_UNIT_RESOLUTION':
        raise ValueError('Native unit resolution not passed')
    unit_models={m['model_id']:m for m in unit_data['models']}
    hashes={unit_path.name:sha(unit_path)}
    models=[]
    for material in ['concrete','timber']:
        path=folder/(material+'-interfaces.json')
        hashes[path.name]=sha(path)
        if hashes[path.name]!=unit_data['inputHashes'][path.name]:
            raise ValueError('Native units bind stale inventory')
        data=json.loads(path.read_text(encoding='utf-8'))
        native={r['ifc_id']:r for r in unit_models[data['model_id']]['rows']}
        source_path=project.parent/'extracted/HVAC/IFC'/(data['model_id']+'.ifc')
        before=sha(source_path)
        if before!=data['sourceSha256']:
            raise ValueError('Original IFC changed')
        print('Read terminal assignments:',material,flush=True)
        source=ifcopenshell.open(str(source_path))
        rows=[]
        for record in data['components']:
            if record['ifc_type']!='IfcAirTerminal':
                continue
            location=record['psets'].get('FI_Sijainti',{})
            flow=record['psets'].get('FI_Tekninen',{}).get('Virtaama')
            metadata=native[record['ifc_id']]['properties']['Virtaama']
            if flow!=metadata['raw_value'] or record['guid']!=native[record['ifc_id']]['guid']:
                raise ValueError('Terminal differs from original unit audit')
            valid=isinstance(flow,(int,float)) and not isinstance(flow,bool) and math.isfinite(flow)
            rows.append({'ifc_id':record['ifc_id'],'guid':record['guid'],'name':record['name'],
                'product_family':product_family(record['name']),'source_floor_label':location.get('Kerros'),
                'source_raw_flow':flow,'flow_m3_s':flow*metadata['resolved_unit']['scale_to_SI'] if valid else None,
                'source_location':location,'source_product':record['psets'].get('FI_Tuote',{}),
                'source_component':record['psets'].get('FI_Komponentti',{}),
                'native_assignments':group_memberships(source.by_id(record['ifc_id'])),
                'status':'SOURCE_TERMINAL_RETAINED; service_and_coincident_demand_not_certified'})
        del source
        after=sha(source_path)
        if before!=after:
            raise ValueError('Original IFC changed during assignment audit')
        assignments=defaultdict(list)
        for row in rows:
            for group in row['native_assignments']:
                assignments[(group['group_type'],group['group_name'])].append(row)
        group_summary=[{'group_type':key[0],'group_name':key[1],'terminal_count':len(items),
            'flow_sum_m3_s':math.fsum(r['flow_m3_s'] for r in items) if all(r['flow_m3_s'] is not None for r in items) else None}
            for key,items in sorted(assignments.items(),key=lambda item:str(item[0]))]
        models.append({'model_id':data['model_id'],'source_sha256':before,'source_sha256_after':after,
            'terminal_count':len(rows),'product_summary':aggregate(rows,'product_family'),
            'floor_summary':aggregate(rows,'source_floor_label'),'native_group_summary':group_summary,'rows':rows})
    result={'artifact_type':'source_terminal_product_and_service_scope_audit','status':'REQUIRES_SERVICE_SCOPE_REVIEW',
        'inputHashes':hashes,'codeSha256':sha(Path(__file__)),'assignmentHelperSha256':sha(Path(__file__).with_name('trace_source_boundary.py')),
        'models':models,'limitations':['Product families are transparent name-based categories, not certification of service function.',
            'Source floor labels do not substitute for checked geometric elevation.',
            'Native assignments can overlap; sums across groups must not be added as disjoint demand.',
            'No terminal excluded, flow adjusted, root assigned or equipment capacity inferred.']}
    (folder/'terminal-service-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps([{'model_id':m['model_id'],'product_summary':m['product_summary'],'floor_summary':m['floor_summary'],
        'native_group_summary':m['native_group_summary'],'other_terminals':[r for r in m['rows'] if r['product_family']=='OTHER_SOURCE_PRODUCT']} for m in models],ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
