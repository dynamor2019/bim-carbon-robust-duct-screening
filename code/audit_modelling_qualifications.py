"""Extract delivery modelling qualifications from original PDFs with page locations."""
import json,re
from pathlib import Path
import fitz
from guard_engineering_inputs import sha

PATTERN=re.compile(r'unit|millimet|\bmm\b|connect|simplif|LOD|accuracy|dimension|duct|Revit|MagiCAD|liit|mitta|yksik|tarkkuu|kanav',re.I)

if __name__=='__main__':
    project=Path(__file__).resolve().parents[1]
    root=project.parent/'extracted/HVAC'
    paths=[root/'0_MEP_standardization_2024.pdf']+[root/'SPECIFICATIONS'/f'HVAC_NordicLCA_Office_{v}_BuildingPermit_BIM_Specification.pdf' for v in ('Concrete','Timbere')]
    folder=project/'.dsh-state/source-extracts/modelling-qualifications'; folder.mkdir(parents=True,exist_ok=True)
    documents=[]; sources=[]
    for path in paths:
        before=sha(path); matches=[]
        with fitz.open(path) as doc:
            for i,page in enumerate(doc):
                text=page.get_text(); lines=text.splitlines()
                target=folder/(path.stem+f'_page{i+1:03}.txt')
                target.write_text(text,encoding='utf-8',newline='')
                hits=[{'line':j+1,'text':line,'context':lines[max(0,j-1):min(len(lines),j+3)]} for j,line in enumerate(lines) if PATTERN.search(line)]
                if hits:
                    matches.append({'physical_page':i+1,'extract_path':str(target),'hits':hits})
                sources.append({'path':str(target),'sha256':sha(target)})
            count=len(doc)
        if sha(path)!=before: raise ValueError('Source changed')
        sources.append({'path':str(path),'sha256':before})
        documents.append({'path':str(path),'pages':count,'matches':matches})
    connection_checks=[]
    for variant in ('concrete','timber'):
        inventory=project/f'milestones/reproducibility/network-interfaces/{variant}-interfaces.json'
        data=json.loads(inventory.read_text(encoding='utf-8'))
        original=project.parent/f"extracted/HVAC/IFC/{data['model_id']}.ifc"
        if sha(original)!=data['sourceSha256']: raise ValueError('Stale original inventory source')
        hits=[{'ifc_id':r['ifc_id'],'pset':name,'value':fields['Liitetty keskuslaitteeseen']} for r in data['components'] for name,fields in r.get('psets',{}).items() if 'Liitetty keskuslaitteeseen' in fields]
        connection_checks.append({'variant':variant,'inventory_components':len(data['components']),'field':'Liitetty keskuslaitteeseen','hits':hits})
        sources.extend([{'path':str(inventory),'sha256':sha(inventory)},{'path':str(original),'sha256':data['sourceSha256']}])
    report={'artifact_type':'delivery_modelling_qualification_source_review','status':'SOURCE_EXTRACTS_REQUIRE_INTERPRETATION','codeSha256':sha(Path(__file__)),
        'source_files':sources,'documents':documents,'native_connection_field_checks':connection_checks,'limitations':['Lexical context extraction does not certify modelling applicability or physical connection.','Sources may describe building permit design rather than installed conditions.'],'formal_experiment':False}
    (project/'milestones/reproducibility/modelling-qualification-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'document_page_counts':[d['pages'] for d in documents],'native_connection_field_checks':connection_checks,'status':report['status']},ensure_ascii=True,indent=2))
