"""Extract cached manufacturer PDFs with page-local text and word positions."""
import hashlib
import json
from pathlib import Path
import fitz


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    project=Path(__file__).resolve().parents[1]
    cache=project/'.dsh-state/parameter-cache'
    output=project/'milestones/reproducibility/parameter-evidence'
    output.mkdir(parents=True,exist_ok=True)
    sources=[('Halton_URH_ULA_EPD_HUB-1432.pdf','https://media.halton.com/app/uploads/2025/02/Halton_supply_exhaust_valves_URH_ULA_EPD_HUB-1432.pdf'),
             ('Halton_URH_fr.pdf','https://media.halton.com/app/uploads/2020/08/Halton_URH_fr.pdf')]
    records=[]
    for filename,url in sources:
        path=cache/filename
        doc=fitz.open(path)
        pages=[]
        for index,page in enumerate(doc,1):
            text_path=cache/(path.stem+f'_page{index:02d}.txt')
            words_path=cache/(path.stem+f'_page{index:02d}_words.json')
            text=page.get_text('text',sort=True)
            text_path.write_text(text,encoding='utf-8',newline='')
            words_path.write_text(json.dumps(page.get_text('words'),ensure_ascii=False)+'\n',encoding='utf-8',newline='')
            pages.append({'physical_page':index,'width_pt':page.rect.width,'height_pt':page.rect.height,
                'text_path':str(text_path),'text_sha256':sha(text_path),'words_path':str(words_path),
                'words_sha256':sha(words_path),'character_count':len(text)})
        records.append({'filename':filename,'url':url,'pdf_sha256':sha(path),'pdf_path':str(path),
            'page_count':len(doc),'metadata':doc.metadata,'pages':pages})
        doc.close()
    result={'artifact_type':'manufacturer_pdf_source_extraction','status':'EXTRACTED_NOT_PARAMETER_QUALIFIED',
        'retrieval_method':'Invoke-WebRequest default certificate validation; URLs linked by official Halton page',
        'codeSha256':sha(Path(__file__)),'PyMuPDF_version':fitz.VersionBind,'sources':records,
        'limitations':['PDF text extraction does not constitute visual validation of dimension drawings or EPD column alignment.',
                       'Product/version, declared-unit and lifecycle-module applicability must be reviewed before adoption.']}
    (output/'manufacturer-pdf-index.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps([{'filename':r['filename'],'page_count':r['page_count'],'pdf_sha256':r['pdf_sha256']} for r in records],indent=2))


if __name__=='__main__':
    main()
