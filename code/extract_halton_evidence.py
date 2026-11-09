"""Extract official Halton HTML evidence and linked documents; no values adopted automatically."""
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

URL='https://www.halton.com/products/urh-en_gb/'


class Extractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ignore=0
        self.text=[]
        self.links=[]
        self.rows=[]
        self.row=None
        self.cell=None
    def handle_starttag(self,tag,attrs):
        attributes=dict(attrs)
        if tag in ('script','style'):
            self.ignore+=1
        if tag=='a' and attributes.get('href'):
            self.links.append(urljoin(URL,attributes['href']))
        if tag=='tr':
            self.row=[]
        if tag in ('td','th') and self.row is not None:
            self.cell=[]
        if tag in ('p','tr','h1','h2','h3','h4','li','br'):
            self.text.append('\n')
    def handle_endtag(self,tag):
        if tag in ('script','style'):
            self.ignore=max(0,self.ignore-1)
        if tag in ('td','th') and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()))
            self.cell=None
            self.text.append(' | ')
        if tag=='tr' and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row=None
    def handle_data(self,data):
        if self.ignore:
            return
        self.text.append(data)
        if self.cell is not None:
            self.cell.append(data)


def main():
    project=Path(__file__).resolve().parents[1]
    html=project/'.dsh-state/parameter-cache/halton-urh.html'
    content=html.read_text(encoding='utf-8')
    parser=Extractor()
    parser.feed(content)
    lines=[' '.join(line.split()) for line in ''.join(parser.text).splitlines()]
    text='\n'.join(line for line in lines if line)+'\n'
    text_path=html.with_suffix('.txt')
    text_path.write_text(text,encoding='utf-8',newline='')
    result={'artifact_type':'official_manufacturer_page_evidence','source_url':URL,
        'source_sha256':hashlib.sha256(html.read_bytes()).hexdigest(),
        'retrieval_method':'PowerShell Invoke-WebRequest using default Windows/.NET certificate validation; no validation bypass',
        'retrieval_command':"Invoke-WebRequest -Uri 'https://www.halton.com/products/urh-en_gb/' -OutFile '.dsh-state/parameter-cache/halton-urh.html'",
        'html_cache':str(html),'text_cache':str(text_path),'text_sha256':hashlib.sha256(text_path.read_bytes()).hexdigest(),
        'table_rows':parser.rows,'document_links':sorted({u for u in parser.links if '.pdf' in u.lower()}),
        'codeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'status':'REQUIRES_MODEL_VERSION_AND_PARAMETER_APPLICABILITY_REVIEW',
        'limitations':['Current manufacturer page is not proof of exact product selection in the 2024 BIM.',
                       'No endpoint offset, pressure requirement or terminal performance coefficient assigned from this extraction.']}
    out=project/'milestones/reproducibility/network-interfaces/halton-urh-source.json'
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'table_rows':parser.rows,'document_links':result['document_links']},ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
