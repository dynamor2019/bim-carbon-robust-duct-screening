"""Compare exported URH mesh features with source connection size and official product dimensions.
Do not create virtual ports or assign manufacturer performance/EPD factors.
"""
import csv
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    project=Path(__file__).resolve().parents[1]
    folder=project/'milestones/reproducibility/network-interfaces'
    manufacturer_path=folder/'halton-urh-source.json'
    manufacturer=json.loads(manufacturer_path.read_text(encoding='utf-8'))
    dimensions={}
    for row in manufacturer['table_rows']:
        if len(row)==5 and row[0] in ('100','125','160','200'):
            dimensions[int(row[0])]={'nominal_size_mm':int(row[0]),'outer_W_mm':float(row[1]),
                'H_mm':float(row[2]),'D_mm':float(row[3]),'mass_kg':float(row[4])}
    if set(dimensions)!={100,125,160,200}:
        raise ValueError('Manufacturer table not parsed unambiguously')
    input_hashes={manufacturer_path.name:sha(manufacturer_path)}
    rows=[]
    summaries=[]
    for material in ['concrete','timber']:
        path=folder/(material+'-interfaces.json')
        input_hashes[path.name]=sha(path)
        data=json.loads(path.read_text(encoding='utf-8'))
        ports_by_component={}
        for port in data['candidate_ports']:
            ports_by_component.setdefault(port['ifc_id'],[]).append(port)
        classified=Counter()
        count=0
        for record in data['components']:
            if record['ifc_type']!='IfcAirTerminal':
                continue
            name=record.get('name','')
            match=re.fullmatch(r'URH/([A-Z])-(\d+)',name)
            if not match or int(match.group(2)) not in dimensions:
                classified['OTHER_TERMINAL_PRODUCT']+=1
                continue
            product=record['psets'].get('FI_Tuote',{})
            if product.get('Tuotetyypin valmistaja','').lower()!='halton':
                classified['URH_NAME_WITHOUT_MATCHED_MANUFACTURER']+=1
                continue
            count+=1
            dims=dimensions[int(match.group(2))]
            features=record.get('features',[])
            radii=[r for p in features for r in p['radii_m']]
            has_outer=any(abs(2*r*1000-dims['outer_W_mm'])<=.01 for r in radii)
            has_nominal=any(abs(2*r*1000-dims['nominal_size_mm'])<=.01 for r in radii)
            has_D=any(abs(2*r*1000-dims['D_mm'])<=.01 for r in radii)
            own_ports=ports_by_component.get(record['ifc_id'],[])
            has_unique=any(p['matching_candidate_count']==1 for p in own_ports)
            if has_outer and not has_nominal and not has_D:
                category='VISIBLE_OUTER_DIMENSION_MATCH_WITHOUT_CONNECTION_SIZE_RIM'
            elif has_nominal or has_D:
                category='HAS_NOMINAL_OR_D_SIZE_GEOMETRIC_RIM_UNVERIFIED_INTERFACE'
            else:
                category='NO_DIMENSION_QUALIFIED_RIM'
            classified[category]+=1
            raw_connection=record['psets'].get('FI_Geometria',{}).get('Liitoskoko (DU)')
            rows.append({'model_id':data['model_id'],'ifc_id':record['ifc_id'],'guid':record['guid'],
                'name':name,'source_connection_size_raw':raw_connection,'nominal_size_mm':dims['nominal_size_mm'],
                'manufacturer_W_mm':dims['outer_W_mm'],'manufacturer_H_mm':dims['H_mm'],'manufacturer_D_mm':dims['D_mm'],
                'exported_rim_diameters_mm':'|'.join(format(2*r*1000,'.9g') for r in sorted(set(radii))),
                'has_numeric_match':has_unique,'classification':category,
                'source_url':manufacturer['source_url'],
                'status':'SOURCE_MODEL_VERSION_AND_INSTALLATION_INTERFACE_UNVERIFIED'})
        summaries.append({'model_id':data['model_id'],'URH_with_matched_manufacturer_count':count,
            'classification_counts':dict(classified),
            'note':'W/H/D retain manufacturer labels; current document dimensions do not establish 2024 frame configuration or endpoint offset.'})
    out=folder/'terminal-dimension-review.csv'
    with out.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    result={'artifact_type':'source_qualified_terminal_geometry_comparison','status':'REQUIRES_REVIEW',
        'inputHashes':input_hashes,'codeSha256':sha(Path(__file__)),'manufacturer_dimension_rows':list(dimensions.values()),
        'models':summaries,'decision':'No port radius changed, no frame offset guessed, no terminal pressure or mass/carbon factor assigned.'}
    (folder/'terminal-dimension-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps(result,ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
