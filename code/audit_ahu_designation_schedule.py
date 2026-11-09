"""Extract original 307 schedule sections as evidence for native AHU designation; no remapping."""
import json,re
from pathlib import Path
import fitz
from recover_fitting_interfaces import sha


def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'milestones/reproducibility'
    pdf=project.parent/'extracted/HVAC/Device-Schedule/Office_concrete_HVAC_Device Schedule_20240611.pdf'
    expected=sha(pdf)
    labels_path=root/'equipment-reference-label-audit.json'
    labels=json.loads(labels_path.read_text(encoding='utf-8'))
    doc=fitz.open(pdf)
    pages=[]
    for i,page in enumerate(doc):
        text=page.get_text('text',sort=True)
        if re.search(r'G3\s+307\s+',text):
            pages.append({'physical_page':i+1,'source_text':text})
    doc.close()
    if sha(pdf)!=expected:
        raise ValueError('Schedule source changed')
    equipment=[]
    for model in labels['models']:
        for fan in model['fans']:
            if fan['name'] in ('Future S09-R-PR','GRA_302TKPK01'):
                equipment.append({'source':model['source'],'name':fan['name'],'selection_reason':'NATIVE_307_AHU_LABEL' if fan['name']=='Future S09-R-PR' else 'LEXICAL_302_NAME_CONTEXT_ONLY','id':fan['ifc_id'],'guid':fan['guid'],'tag':fan['tag'],
                    'description':fan['description'],'declared_device_code':fan['psets'].get('FI_Komponentti',{}).get('Laitetunnus'),
                    'manufacturer':fan['psets'].get('FI_Tuote',{}).get('Tuotetyypin valmistaja'),
                    'group_memberships':fan['native_group_memberships']})
    report={'artifact_type':'native_307_AHU_designation_and_primary_schedule_pages','status':'AHU_DESIGNATION_EVIDENCE_ONLY; PF01_CORRESPONDENCE_UNCERTIFIED',
        'inputHashes':{labels_path.name:sha(labels_path)},'source_files':[{'path':str(pdf),'sha256':expected}],
        'codeSha256':sha(Path(__file__)),'equipment':equipment,'schedule_307_pages':pages,
        'limitations':['Native 307TK_PK01 designation supports an AHU-level label, not a physical port or fan assignment.',
            'Original schedule values are not transferred across 307 and 302 systems; no demand rescaling or field filling.',
            '307 schedule extraction searches original printed tokens and retains whole physical-page text, including adjacent sections.']}
    (root/'ahu-designation-schedule-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'equipment':equipment,'schedule_307_pages':pages},ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
