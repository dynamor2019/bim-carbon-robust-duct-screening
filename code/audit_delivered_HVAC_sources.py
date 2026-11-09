"""Inventory HVAC delivered files; extract office schedule evidence without inventing connections."""
import json,re
from pathlib import Path
import fitz
from guard_engineering_inputs import sha

TOKENS=re.compile(r'302\s*(?:PF|PK|TK)|307\s*(?:PF|PK|TK)|Future\s*S09|fan\s*curve|selection|connection|connectivity|schematic|pohjapiirust|Seinämäpaksuus|Pyöreä kierresauma|Säätöpelti',re.I)


def main():
    project=Path(__file__).resolve().parents[1]
    source_root=project.parent/'extracted/HVAC'
    paths=sorted(p for p in source_root.rglob('*') if p.is_file())
    inventory=[{'relative':str(p.relative_to(source_root)),'bytes':p.stat().st_size,'extension':p.suffix.lower()} for p in paths]
    selected=[source_root/'Device-Schedule'/name for name in ('Office_concrete_Ventilation_Network components_20240611.pdf','Office_concrete_HVAC_Materials by systems_20240611.pdf')]
    extracts=project/'.dsh-state/source-extracts/delivered-office-schedules'
    extracts.mkdir(parents=True,exist_ok=True)
    documents=[]
    for path in selected:
        before=sha(path)
        pages=[]
        with fitz.open(path) as document:
            for i,page in enumerate(document):
                text=page.get_text()
                hits=[{'line':j,'text':line} for j,line in enumerate(text.splitlines(),1) if TOKENS.search(line)]
                target=extracts/(path.stem+f'_page{i+1:03}.txt')
                target.write_text(text,encoding='utf-8',newline='')
                if hits:
                    pages.append({'physical_page':i+1,'extract_path':str(target),'extract_sha256':sha(target),'hits':hits,
                        'original_words_xy':page.get_text('words') if path.name.startswith('Office_concrete_HVAC_Materials') and i==18 else []})
            count=len(document)
        if sha(path)!=before:
            raise ValueError('Source document changed during extraction')
        documents.append({'path':str(path),'sha256':before,'page_count':count,'matched_pages':pages})
    report={'artifact_type':'delivered_HVAC_inventory_and_office_schedule_evidence','status':'DELIVERY_AND_SCHEDULE_EVIDENCE_ONLY','codeSha256':sha(Path(__file__)),
        'source_files':[{'path':d['path'],'sha256':d['sha256']} for d in documents]+[{'path':p['extract_path'],'sha256':p['extract_sha256']} for d in documents for p in d['matched_pages']],
        'file_inventory':inventory,'documents':documents,'limitations':['File inventory is local extracted delivery only; it is not proof no other drawing/selection exists.',
            'Lexical matches retain original page/line text, not a physical connection or fan identity certificate.',
            'Native RVT files are present; no Revit API extraction or connector certification claimed.']}
    target=project/'milestones/reproducibility/delivered-HVAC-source-review.json'
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':report['status'],'file_count':len(paths),'documents':[{'name':Path(d['path']).name,'pages':d['page_count'],'matches':[{'physical_page':p['physical_page'],'hits':p['hits']} for p in d['matched_pages']]} for d in documents]},ensure_ascii=True,indent=2))


if __name__=='__main__': main()
