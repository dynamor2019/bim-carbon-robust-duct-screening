"""Acquire linked official PDF and formula asset locations; keep source versions distinct."""
import json,urllib.request,re
from pathlib import Path
import fitz
from guard_engineering_inputs import sha

if __name__=='__main__':
    project=Path(__file__).resolve().parents[1]; folder=project/'.dsh-state/manufacturer-cache/halton-pra'
    original=json.loads((folder/'official-product.json').read_text(encoding='utf-8'))
    content=original['content']['rendered']
    snippets=[]
    for match in re.finditer(r'formula',content,re.I):
        snippets.append(content[max(0,match.start()-200):match.start()+1600])
    url='https://media.halton.com/app/uploads/2020/08/Halton_PRA_fr.pdf'
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'application/pdf'})
    with urllib.request.urlopen(req,timeout=60) as response: raw=response.read()
    if not raw.startswith(b'%PDF'): raise ValueError('Not PDF content')
    pdf=folder/'official-PRA-fr.pdf'; pdf.write_bytes(raw)
    docs=[]
    with fitz.open(pdf) as document:
        for i,page in enumerate(document):
            path=folder/f'official-PRA-fr-page{i+1:03}.txt'; path.write_text(page.get_text(),encoding='utf-8',newline='')
            docs.append({'physical_page':i+1,'path':str(path),'sha256':sha(path)})
    manifest={'url':url,'pdf_path':str(pdf),'pdf_sha256':sha(pdf),'page_count':len(docs),'extracted_pages':docs,
        'formula_html_contexts':snippets,'product_json_sha256':sha(folder/'official-product.json'),'acquisition_code_sha256':sha(Path(__file__)),
        'limits':['2020/08 URL path is not proof of document publication date.','French linked PDF may have different revision/product scope from current English page.']}
    (folder/'technical-acquisition.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'pdf_pages':len(docs),'formula_contexts':snippets},ensure_ascii=True,indent=2))
