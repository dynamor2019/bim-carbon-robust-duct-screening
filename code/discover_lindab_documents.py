"""Trace official Lindab product-to-EPD links and extract only selected duct/fitting PDFs."""
import json
import subprocess
from pathlib import Path
from urllib.parse import urljoin,urlparse
import fitz
import extract_halton_evidence as base
from recover_fitting_interfaces import sha

BASE='https://www.lindab.com/'


class RowLinks(base.Extractor):
    def __init__(self):
        super().__init__()
        self.row_links=[]
        self.linked_rows=[]
    def handle_starttag(self,tag,attrs):
        if tag=='tr':
            self.row_links=[]
        super().handle_starttag(tag,attrs)
        if tag=='a' and self.row is not None:
            href=dict(attrs).get('href')
            if href:
                self.row_links.append(urljoin(BASE,href))
    def handle_endtag(self,tag):
        if tag=='tr' and self.row:
            self.linked_rows.append({'cells':list(self.row),'links':list(self.row_links)})
        super().handle_endtag(tag)


def main():
    project=Path(__file__).resolve().parents[1]
    cache=project/'.dsh-state/parameter-cache'
    html=cache/'lindab-document-search.html'
    base.URL=BASE
    parser=RowLinks()
    parser.feed(html.read_text(encoding='utf-8'))
    chosen=[r for r in parser.linked_rows if r['cells'][0] in ('SR','SRL','BFU')]
    if not chosen:
        raise ValueError('No product-linked duct EPD rows found')
    urls=sorted({u for r in chosen for u in r['links'] if '.pdf' in u.lower()})
    documents=[]
    for url in urls:
        parsed=urlparse(url)
        if parsed.scheme!='https' or parsed.netloc!='www.lindab.com' or not parsed.path.lower().endswith('.pdf'):
            raise ValueError('Unexpected official document URL')
        filename='lindab_'+Path(parsed.path).name
        path=cache/filename
        if not path.exists():
            quoted_url=url.replace("'","''")
            quoted_path=str(path).replace("'","''")
            result=subprocess.run(['pwsh','-NoProfile','-Command',f"Invoke-WebRequest -Uri '{quoted_url}' -OutFile '{quoted_path}'"],capture_output=True)
            if result.returncode:
                failure={'url':url,'returncode':result.returncode,'stderr':result.stderr.decode('utf-8','replace')}
                (cache/'lindab-retrieval-failure.json').write_text(json.dumps(failure,indent=2)+'\n',encoding='utf-8')
                raise RuntimeError('Official EPD retrieval failed; retained failure, no factor adopted')
        doc=fitz.open(path)
        pages=[]
        for index,page in enumerate(doc,1):
            text_path=cache/(path.stem+f'_page{index:02d}.txt')
            words_path=cache/(path.stem+f'_page{index:02d}_words.json')
            text_path.write_text(page.get_text('text',sort=True),encoding='utf-8',newline='')
            words_path.write_text(json.dumps(page.get_text('words'),ensure_ascii=False)+'\n',encoding='utf-8',newline='')
            pages.append({'physical_page':index,'text_path':str(text_path),'text_sha256':sha(text_path),
                'words_path':str(words_path),'words_sha256':sha(words_path)})
        products=sorted({r['cells'][0] for r in chosen if url in r['links']})
        documents.append({'filename':filename,'url':url,'products_from_official_rows':products,
            'pdf_sha256':sha(path),'page_count':len(doc),'pages':pages})
        doc.close()
    output=project/'milestones/reproducibility/parameter-evidence/lindab-document-index.json'
    result={'artifact_type':'official_duct_epd_discovery','status':'EXTRACTED_NOT_PARAMETER_QUALIFIED',
        'htmlSha256':sha(html),'codeSha256':sha(Path(__file__)),'parserSha256':sha(Path(base.__file__)),
        'source_url':'https://www.lindab.com/document-search/?query=EPD&sort=popularity&display=16&page=1&sortDir=asc',
        'selected_product_rows':chosen,'documents':documents,
        'retrieval_method':'Default Windows/.NET TLS validation; existing cached PDFs reused.',
        'limitations':['Source generic FeZn BIM does not identify Lindab as actual manufacturer.',
            'Do not adopt low-carbon steel, fitting, silencer or other product factors as generic duct factors.']}
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps([{k:r[k] for k in ['filename','products_from_official_rows','pdf_sha256','page_count']} for r in documents],indent=2),flush=True)


if __name__=='__main__':
    main()
