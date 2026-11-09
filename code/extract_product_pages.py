"""Extract official cached product pages with source URLs and table/link evidence."""
import argparse
import json
from pathlib import Path
import extract_halton_evidence as parser_module
from recover_fitting_interfaces import sha


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('filename')
    parser.add_argument('url')
    args=parser.parse_args()
    project=Path(__file__).resolve().parents[1]
    cache=project/'.dsh-state/parameter-cache'
    source=(cache/args.filename).resolve()
    if not source.is_relative_to(cache.resolve()):
        raise ValueError('Source must be in project cache')
    parser_module.URL=args.url
    extractor=parser_module.Extractor()
    extractor.feed(source.read_text(encoding='utf-8'))
    lines=[' '.join(line.split()) for line in ''.join(extractor.text).splitlines()]
    text='\n'.join(line for line in lines if line)+'\n'
    text_path=source.with_suffix('.txt')
    text_path.write_text(text,encoding='utf-8',newline='')
    result={'artifact_type':'official_product_page_extraction','status':'SOURCE_EXTRACTED_APPLICABILITY_PENDING',
        'source_url':args.url,'html_sha256':sha(source),'text_path':str(text_path),'text_sha256':sha(text_path),
        'table_rows':extractor.rows,'pdf_links':sorted({u for u in extractor.links if '.pdf' in u.lower()}),
        'product_links':sorted({u for u in extractor.links if '/products/' in u.lower()}),
        'codeSha256':sha(Path(__file__)),'parserSha256':sha(Path(parser_module.__file__)),
        'retrieval_method':'Invoke-WebRequest default certificate validation; no factors adopted'}
    folder=project/'milestones/reproducibility/parameter-evidence'
    folder.mkdir(parents=True,exist_ok=True)
    (folder/(source.stem+'-source.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'pdf_links':result['pdf_links'],'product_links':[u for u in result['product_links'] if 'prl' in u.lower()],
        'table_rows':result['table_rows']},ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
