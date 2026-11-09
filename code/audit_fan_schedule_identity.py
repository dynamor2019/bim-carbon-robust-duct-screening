"""Retain exact fan/AHU/filter schedule sections and compare to decoded IFC identity evidence."""
import json,re
from pathlib import Path
import fitz
from recover_fitting_interfaces import sha


def section(text,pattern):
    start=re.search(pattern,text)
    if not start:
        raise ValueError('Expected schedule designation missing')
    stop=re.search(r'\n\s*G3\s+\d',text[start.end():])
    end=start.end()+stop.start() if stop else len(text)
    return text[start.start():end].strip()


def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'milestones/reproducibility'
    labels_path=root/'equipment-reference-label-audit.json'
    labels=json.loads(labels_path.read_text(encoding='utf-8'))
    pdf=project.parent/'extracted/HVAC/Device-Schedule/Office_concrete_HVAC_Device Schedule_20240611.pdf'
    expected=sha(pdf)
    doc=fitz.open(pdf)
    records=[]
    for page,label,pattern in ((31,'302PK01',r'G3\s+302\s+PK\s+01'),(32,'302PF01',r'G3\s+302\s+PF\s+01'),(32,'302S19',r'G3\s+302\s+S\s+19')):
        text=section(doc[page-1].get_text('text',sort=True),pattern)
        records.append({'designation':label,'physical_page':page,'extracted_source_text':text,
            'note':'Original source values and blank performance fields retained; no table value backfilled.'})
    doc.close()
    if sha(pdf)!=expected:
        raise ValueError('Source PDF changed')
    report={'artifact_type':'schedule_and_decoded_IFC_equipment_identity_comparison','status':'FAN_IDENTITY_AND_PERFORMANCE_UNCERTIFIED',
        'inputHashes':{labels_path.name:sha(labels_path)},'source_files':[{'path':str(pdf),'sha256':expected}],
        'codeSha256':sha(Path(__file__)),'schedule_records':records,
        'IFC_label_counts':[{'source':m['source'],'counts':m['token_hit_counts']} for m in labels['models'] if m['discipline']=='hvac'],
        'limitations':['Stored label search does not establish correspondence when a designation is absent or differently encoded.',
            'Schedule exhaust design flow is not maximum fan capacity; duct total pressure loss is not certified total fan rise.',
            'Filter left-office description and fan/right-office service labels require design clarification; no exclusion inferred.']}
    (root/'fan-schedule-identity-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps(report,ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
