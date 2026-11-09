"""Cache official PTS source and retain linked model fields without assigning units."""
import json,re,html,urllib.request
from pathlib import Path
from collections import Counter
from guard_engineering_inputs import sha

if __name__=='__main__':
    project=Path(__file__).resolve().parents[1]; root=project/'milestones/reproducibility'; cache=project/'.dsh-state/manufacturer-cache/halton-pts';cache.mkdir(parents=True,exist_ok=True)
    url='https://www.halton.com/wp-json/wp/v2/product/32035'
    request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json'})
    src=cache/'official-product.json'
    if src.exists():
        raw=src.read_bytes()
    else:
        with urllib.request.urlopen(request,timeout=60) as response: raw=response.read()
        src.write_bytes(raw)
    data=json.loads(raw)
    content=data['content']['rendered'];clean=re.sub(r'<(script|style)\b[^>]*>.*?</\1>','',content,flags=re.S|re.I)
    text=html.unescape(re.sub(r'<[^>]+>','\n',clean));lines=[re.sub(r'\s+',' ',s).strip() for s in text.splitlines() if s.strip()]
    txt=cache/'official-product.txt';txt.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='')
    inventory=root/'halton-pra-object-audit.json';inv=json.loads(inventory.read_text(encoding='utf-8'));models=[]
    for model in inv['models']:
        rows=[r for r in model['rows'] if any(str(h['value']).endswith('/PTS') for h in r['product_matches'])]
        selected=[{'ifc_id':r['ifc_id'],'guid':r['guid'],'name':r['name'],'technical_fields_native':r['psets'].get('FI_Tekninen',{}),'geometry_fields_native':r['psets'].get('FI_Geometria',{})} for r in rows]
        distributions={key:dict(Counter(str(r['technical_fields_native'].get(key)) for r in selected)) for key in ('Painehäviö','Esisäätöarvo, laskettu','Virtaama')}
        counts=dict(Counter(r['name'] for r in rows));models.append({'technical_native_value_counts':distributions,'variant':model['variant'],'object_count':len(rows),'name_counts':counts,'objects':selected})
    report={'artifact_type':'PTS_manufacturer_and_object_field_review','status':'PTS_SOURCE_AND_NATIVE_FIELDS_NOT_HYDRAULIC_VALIDATION','codeSha256':sha(Path(__file__)),'source_files':[{'path':str(p),'sha256':sha(p)} for p in (src,txt,inventory)],'official_api':url,'official_page':data['link'],'modified_gmt':data['modified_gmt'],'download_links':sorted(set(html.unescape(x) for x in re.findall(r'href=[\"\x27]([^\"\x27]+)',content) if '.pdf' in x or 'ehit' in x)),'models':models,'formal_experiment':False,'limits':['Native cached values do not preserve IFC measure type or unit override; no unit or angle interpretation assigned here.','Calculated preset and model loss are not independent measured commissioning evidence.','Current manufacturer page does not certify installed 2024 revision or physically connected service.','No 15 Pa constant extrapolation across new route/flow/diameter designs.']}
    (root/'halton-pts-source-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':report['status'],'page':data['link'],'models':[{k:v for k,v in m.items() if k!='objects'} for m in models],'download_links':report['download_links']},ensure_ascii=False,indent=2))
