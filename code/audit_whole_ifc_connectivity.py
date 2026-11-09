"""Bounded lexical audit of original IFC relationship entity declarations.
Not a complete STEP parser or a certification of physical connections.
"""
import re,json
from collections import Counter
from pathlib import Path
from guard_engineering_inputs import sha

KINDS=('IFCDISTRIBUTIONPORT','IFCRELCONNECTSPORTS','IFCRELCONNECTSPORTTOELEMENT','IFCRELCONNECTSELEMENTS',
       'IFCRELCONNECTSWITHREALIZINGELEMENTS','IFCRELNESTS','IFCRELAGGREGATES','IFCRELSERVICESBUILDINGS',
       'IFCRELASSIGNSTOGROUP','IFCRELDEFINESBYTYPE')
DECLARATION=re.compile(r'^\s*#(\d+)\s*=\s*([A-Z0-9_]+)\s*\(')


def scan(path):
    counts=Counter(); connection_records=[]; malformed=[]; open_record=''; line_start=0
    with path.open('r',encoding='utf-8-sig',errors='strict') as stream:
        for line_number,line in enumerate(stream,1):
            if not open_record:
                if not line.lstrip().startswith('#'): continue
                line_start=line_number
            open_record+=line
            # Source export uses semicolon termination at the end of each entity.
            # Reject unsupported multiline/string delimiters rather than partial counting.
            if not line.rstrip().endswith(';'): continue
            match=DECLARATION.match(open_record)
            if not match:
                malformed.append(line_start)
            else:
                kind=match.group(2); counts[kind]+=1
                if kind in KINDS and kind not in ('IFCRELASSIGNSTOGROUP','IFCRELDEFINESBYTYPE','IFCRELAGGREGATES'):
                    connection_records.append({'ifc_id':int(match.group(1)),'kind':kind,'source_line':line_start,
                        'raw_step_record':open_record.strip(),'reference_ids':[int(x) for x in re.findall(r'#(\d+)',open_record.split('=',1)[1])]})
            open_record=''
    if open_record or malformed: raise ValueError('Unsupported entity record boundary/schema; no incomplete counting')
    return {'entity_count':sum(counts.values()),'selected_kind_counts':{k:counts[k] for k in KINDS},'records':connection_records,
        'all_kind_counts':dict(sorted(counts.items()))}


def main():
    project=Path(__file__).resolve().parents[1]; sources=[]; models=[]
    for variant in ('Concrete','Timber'):
        path=project.parent/f'extracted/HVAC/IFC/HVAC_NordicLCA_Office_{variant}_BuildingPermit.ifc'
        before=sha(path); print('Scan connectivity declarations:',variant,flush=True)
        result=scan(path)
        if sha(path)!=before: raise ValueError('Source changed during scan')
        inventory=project/f'milestones/reproducibility/network-interfaces/{variant.lower()}-interfaces.json'
        data=json.loads(inventory.read_text(encoding='utf-8'))
        if data['sourceSha256']!=before: raise ValueError('Stale system inventory')
        members={r['ifc_id'] for r in data['components']}
        result['selected_records_referencing_native_system_members']=[r['ifc_id'] for r in result['records'] if set(r['reference_ids'])&members]
        models.append({'variant':variant,**result})
        sources.extend([{'path':str(path),'sha256':before},{'path':str(inventory),'sha256':sha(inventory)}])
    report={'artifact_type':'whole_original_IFC_connectivity_declaration_audit','status':'PASS_LEXICAL_DECLARATION_SCAN_ONLY','codeSha256':sha(Path(__file__)),
        'helperHashes':{'guard_engineering_inputs.py':sha(Path(__file__).with_name('guard_engineering_inputs.py'))},'source_files':sources,'models':models,
        'limitations':['Lexical entity-class existence and referenced IDs are not physical connectivity or direction certification.',
            'No STEP argument semantics or global graph traversals are inferred from co-occurring reference IDs.',
            'Missing exported relations do not prove absent native RVT connectors or absent physical installations.',
            'Only this exporter record termination style is supported; arbitrary STEP strings/multiple entities per line require a full parser.'],
        'formal_experiment':False}
    (project/'milestones/reproducibility/whole-IFC-connectivity-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps([{'variant':m['variant'],'entity_count':m['entity_count'],'counts':m['selected_kind_counts'],'selected_record_member_reference_count':len(m['selected_records_referencing_native_system_members'])} for m in models],indent=2))

if __name__=='__main__': main()
