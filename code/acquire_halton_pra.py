"""Acquire official manufacturer product record and retain raw content/hash."""
import json,urllib.request,re,html
from pathlib import Path
from guard_engineering_inputs import sha

if __name__=='__main__':
    project=Path(__file__).resolve().parents[1]; folder=project/'.dsh-state/manufacturer-cache/halton-pra'; folder.mkdir(parents=True,exist_ok=True)
    url='https://www.halton.com/wp-json/wp/v2/product/31992'
    request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json'})
    with urllib.request.urlopen(request,timeout=60) as r: raw=r.read()
    target=folder/'official-product.json'; target.write_bytes(raw); data=json.loads(raw)
    content=data['content']['rendered']
    content=re.sub(r'<(script|style)\b[^>]*>.*?</\1>','',content,flags=re.S|re.I)
    text=html.unescape(re.sub(r'<[^>]+>','\n',content))
    lines=[re.sub(r'\s+',' ',s).strip() for s in text.splitlines() if s.strip()]
    text_path=folder/'official-product.txt'; text_path.write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='')
    links=sorted(set(html.unescape(x) for x in re.findall(r'href=[\"\x27]([^\"\x27]+)',data['content']['rendered'])))
    manifest={'official_api':url,'official_page':data['link'],'id':data['id'],'modified_gmt':data['modified_gmt'],'raw_sha256':sha(target),'text_sha256':sha(text_path),'links':links}
    (folder/'acquisition.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'page':data['link'],'text_lines':len(lines),'technical_links':[x for x in links if '.pdf' in x or 'ehit' in x]},indent=2))
