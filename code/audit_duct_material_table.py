"""Coordinate-based page-19 material specification extraction, not installed mass."""
import re,json
from pathlib import Path
import fitz
from guard_engineering_inputs import sha


def pair_rows(lines,tolerance_pt=.1):
    headers=sorted([r for r in lines if r['text'].startswith(('Pyöreä kierresauma,','Suorakaide, kuumasinkitty,'))],key=lambda r:r['bbox'][1])
    if len(headers)!=7:
        raise ValueError('Expected exactly seven explicit duct specification headers')
    rows=[]
    for i,header in enumerate(headers):
        lower=header['bbox'][1]
        upper=headers[i+1]['bbox'][1] if i+1<len(headers) else 750.
        fields=[r for r in lines if lower<r['bbox'][1]<upper and r['text']=='Seinämäpaksuus mm']
        if len(fields)!=1:
            raise ValueError('Missing/ambiguous thickness field in section')
        field=fields[0]
        candidates=[r for r in lines if r['bbox'][0]>field['bbox'][2] and abs(r['bbox'][1]-field['bbox'][1])<=tolerance_pt and re.fullmatch(r'\d+,\d+',r['text'])]
        if len(candidates)!=1:
            raise ValueError('Missing/ambiguous same-row thickness value')
        value=candidates[0]
        rows.append({'source_label':header['text'],'wall_thickness_mm':float(value['text'].replace(',','.')),
            'header_bbox_pt':header['bbox'],'field_bbox_pt':field['bbox'],'value_bbox_pt':value['bbox'],'value_text':value['text'],
            'scope':'PROJECT_SPECIFICATION_ONLY','installed_mass_certified':False})
    return rows


def main():
    project=Path(__file__).resolve().parents[1]
    source=project.parent/'extracted/HVAC/Device-Schedule/Office_concrete_HVAC_Materials by systems_20240611.pdf'
    source_hash=sha(source)
    with fitz.open(source) as doc:
        page=doc[18]
        lines=[{'text':''.join(s['text'] for s in line['spans']),'bbox':list(line['bbox'])} for block in page.get_text('dict')['blocks'] for line in block.get('lines',[])]
        rows=pair_rows(lines)
        words=page.get_text('words')
        for row in rows:
            # Alternative word extraction independently checks the numeric glyph and location.
            matches=[w for w in words if w[4]==row['value_text'] and abs(w[1]-row['value_bbox_pt'][1])<.1 and abs(w[0]-row['value_bbox_pt'][0])<.1]
            if len(matches)!=1:
                raise ValueError('Word-level numeric location cross-check failed')
            row['word_location_crosscheck']='PASS'
    if sha(source)!=source_hash:
        raise ValueError('Source hash changed')
    report={'artifact_type':'project_duct_material_coordinate_pairing','status':'PASS_SOURCE_TABLE_PAIRING_ONLY','codeSha256':sha(Path(__file__)),
        'source_files':[{'path':str(source),'sha256':source_hash}], 'physical_page':19,'rows':rows,'coordinate_tolerance_pt':.1,
        'unresolved':['Diameter bands do not cover every intermediate size; no gap interpolation.', 'Kitchen local exhaust category is separate; no transfer to office general exhaust.',
            'No steel density, nominal diameter convention, seams/flanges/coatings or product quantity inferred.', 'Coordinate/text agreement is not independent scientific validation or visual QA.']}
    target=project/'milestones/reproducibility/duct-material-table-audit.json'
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':report['status'],'rows':[{'label':r['source_label'],'thickness_mm':r['wall_thickness_mm']} for r in rows]},ensure_ascii=True,indent=2))

if __name__=='__main__': main()
