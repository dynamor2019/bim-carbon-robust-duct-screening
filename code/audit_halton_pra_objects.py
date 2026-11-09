"""Audit source product identifiers in cached named-system inventory, not physical topology."""
import json,re
from pathlib import Path
from guard_engineering_inputs import sha
PRA=re.compile(r'(?<![A-Za-z])PRA(?![A-Za-z])',re.I)
BRAND=re.compile(r'halton',re.I)
SETTING=re.compile(r'adjust|setting|position|säät|saato|asento|opening|avaus',re.I)

def walk(value,path=''):
    if isinstance(value,dict):
        for key,item in value.items(): yield from walk(item,path+'/'+str(key))
    elif isinstance(value,list):
        for i,item in enumerate(value): yield from walk(item,path+'/'+str(i))
    else: yield path,value

if __name__=='__main__':
    project=Path(__file__).resolve().parents[1]; root=project/'milestones/reproducibility'; sources=[]; models=[]
    for variant in ('concrete','timber'):
        file=root/f'network-interfaces/{variant}-interfaces.json'; data=json.loads(file.read_text(encoding='utf-8'))
        raw=project.parent/f'extracted/HVAC/IFC/HVAC_NordicLCA_Office_{variant.title()}_BuildingPermit.ifc'
        if sha(raw)!=data['sourceSha256'] or data['sourceSha256_after']!=data['sourceSha256']: raise ValueError('Interface source hash stale')
        if data['system_name']!='302PK01 (toimistot, oikea)': raise ValueError('Unexpected system scope')
        rows=[]
        for component in data['components']:
            scoped={'name':component['name'],'psets':component['psets']}
            fields=list(walk(scoped)); hits=[{'field_path':p,'value':v,'match_role':'PRA' if PRA.search(str(v)) else 'Halton'} for p,v in fields if PRA.search(str(v)) or BRAND.search(str(v))]
            if not hits: continue
            rows.append({'ifc_id':component['ifc_id'],'guid':component['guid'],'ifc_type':component['ifc_type'],'name':component['name'],'product_matches':hits,'setting_named_fields':[{'field_path':p,'value':v} for p,v in fields if SETTING.search(p)],'psets':component['psets']})
        sources.extend([{'path':str(file),'sha256':sha(file)},{'path':str(raw),'sha256':sha(raw)}])
        product_links={}; setting_fields={}
        for row in rows:
            for hit in row['product_matches']:
                if 'valmistajan linkki' in hit['field_path']:
                    link=str(hit['value']); product_links[link]=product_links.get(link,0)+1
            for field in row['setting_named_fields']:
                key=field['field_path']; setting_fields[key]=setting_fields.get(key,0)+1
        models.append({'explicit_manufacturer_product_links':product_links,'setting_named_field_counts':setting_fields,'variant':variant,'named_group_ifc_id':data['group_ifc_id'],'inventory_count':len(data['components']),'product_match_count':len(rows),'PRA_match_count':sum(any(h['match_role']=='PRA' for h in r['product_matches']) for r in rows),'rows':rows})
    report={'artifact_type':'302PK01_PRA_native_product_identifier_audit','status':'PRODUCT_IDENTIFIER_SOURCE_AUDIT_ONLY','codeSha256':sha(Path(__file__)),'source_files':sources,'models':models,'formal_experiment':False,'limits':['Named-system inventory only, not whole IFC product search or certified physical service.','Product token match is not product revision, installed setting, flow or pressure-loss applicability.','Setting keyword matches retained without interpreting them as iris setting.','No manufacturer coefficient adopted.']}
    (root/'halton-pra-object-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':report['status'],'models':[{k:v for k,v in m.items() if k!='rows'} for m in models]},indent=2))
