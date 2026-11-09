"""Inspect original page coordinates; never infer pairing from extraction order."""
from pathlib import Path
import fitz,json

if __name__=='__main__':
    project=Path(__file__).resolve().parents[1]
    source=project.parent/'extracted/HVAC/Device-Schedule/Office_concrete_HVAC_Materials by systems_20240611.pdf'
    with fitz.open(source) as doc:
        page=doc[18]
        lines=[]
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines',[]):
                text=''.join(s['text'] for s in line['spans'])
                lines.append({'bbox':line['bbox'],'text':text})
        print(json.dumps(sorted(lines,key=lambda x:(x['bbox'][1],x['bbox'][0])),ensure_ascii=True,indent=2))
        print('RULES',json.dumps([{'rect':list(d['rect']),'items':[(i[0],[list(v) if hasattr(v,'__iter__') else v for v in i[1:]]) for i in d['items']]} for d in page.get_drawings() if d['rect'].width>100],default=str))
