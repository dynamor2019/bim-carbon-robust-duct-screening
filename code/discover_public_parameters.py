"""Cache public official parameter page resources for later evidence qualification."""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


def fetch(url):
    with urlopen(Request(url,headers={'User-Agent':'BIM-Research-Source-Audit/1.0'}), timeout=30) as response:
        return response.read(), response.geturl(), response.headers.get('Content-Type','')


def main():
    project=Path(__file__).resolve().parents[1]
    cache=project/'.dsh-state/parameter-cache'
    cache.mkdir(parents=True,exist_ok=True)
    base='https://co2data.fi/rakentaminen/'
    try:
        data,url,mime=fetch(base)
    except Exception as error:
        result={'status':'ACCESS_FAILED_NO_FACTORS_ADOPTED', 'url':base,
                'error':str(error), 'certificate_verification':'retained; no unverified TLS fallback',
                'fallback':'Official page successfully fetched through web_fetch; exact resource and factor records still unavailable.',
                'codeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        output=project/'milestones/reproducibility/boundary-evidence/public-parameter-resources.json'
        output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
        print(json.dumps(result,ensure_ascii=True,indent=2))
        raise SystemExit(2)
    (cache/'co2data-page.html').write_bytes(data)
    scripts=re.findall(r'<script[^>]+src=[\"\x27]([^\"\x27]+)',data.decode('utf-8'),flags=re.I)
    records=[{'url':url,'mime':mime,'sha256':hashlib.sha256(data).hexdigest(),'cache':'co2data-page.html'}]
    for index,resource in enumerate(scripts):
        target=urljoin(base,resource)
        if urlparse(target).netloc!='co2data.fi':
            continue
        try:
            body,final,kind=fetch(target)
            name=f'co2data-script{index}.js'
            (cache/name).write_bytes(body)
            text=body.decode('utf-8',errors='replace')
            candidates=sorted(set(re.findall(r'[\"\x27]([^\"\x27\s]+\.json(?:\?[^\"\x27\s]*)?)[\"\x27]',text)))
            records.append({'url':final,'mime':kind,'sha256':hashlib.sha256(body).hexdigest(),
                            'cache':name,'json_resource_strings':candidates})
        except Exception as error:
            records.append({'url':target,'status':'ACCESS_FAILED','error':str(error)})
    result={'status':'DISCOVERY_ONLY_NO_FACTORS_ADOPTED', 'official_provider':'Finnish Environment Institute (Syke)',
            'scope':'public construction emission database web resources', 'records':records,
            'limitations':['No product factor can be applied until record version, scope, unit, market and background report are checked.',
                           'Generic database factors are not product-specific EPDs.'],
            'codeSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    out=project/'milestones/reproducibility/boundary-evidence/public-parameter-resources.json'
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps(result,ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
