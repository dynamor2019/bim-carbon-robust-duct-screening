"""Qualify Lindab reference duct weight/carbon catalogue without assigning BIM factors."""
import json
import re
from pathlib import Path
from recover_fitting_interfaces import sha


def parse_weights(text,words):
    if 'Standard weight' not in text or '(kg/m)' not in text:
        raise ValueError('Annex weight-per-metre unit missing')
    rows=[]
    for line in text.splitlines():
        match=re.fullmatch(r'\s*(\d+)\s+(\d+)\s+(\d+(?:\.\d+)?)\s*',line)
        if match:
            diameter,length,weight=match.groups()
            rows.append({'diameter_mm':int(diameter),'stock_length_mm':int(length),'mass_kg_per_m':float(weight)})
    clusters=[]
    for word in sorted(words,key=lambda w:(w[1]+w[3])/2):
        if not re.fullmatch(r'\d+(?:\.\d+)?',word[4]):
            continue
        y=(word[1]+word[3])/2
        for cluster in clusters:
            if abs(cluster['y']-y)<=2:
                cluster['words'].append(word)
                break
        else:
            clusters.append({'y':y,'words':[word]})
    independently=[]
    for cluster in clusters:
        if len(cluster['words'])!=3:
            continue
        ordered=sorted(cluster['words'],key=lambda w:w[0])
        if not ordered[0][4].isdigit() or not ordered[1][4].isdigit():
            continue
        independently.append({'diameter_mm':int(ordered[0][4]),'stock_length_mm':int(ordered[1][4]),'mass_kg_per_m':float(ordered[2][4])})
    if rows!=independently or not rows:
        raise ValueError('Text and coordinate-based weight table extractions disagree')
    if len({r['diameter_mm'] for r in rows})!=len(rows) or any(min(r.values())<=0 for r in rows):
        raise ValueError('Duplicate diameter or nonpositive catalogue value')
    return rows


def summary_factor(text,metric):
    match=re.search(r'GWP-'+metric+r',\s*A1-A3\s*\(kgCO2e\)\s*([\d.,]+)',text)
    if match is None:
        raise ValueError('Summary GWP metric missing')
    return float(match.group(1).replace(',','.'))


def main():
    project=Path(__file__).resolve().parents[1]
    cache=project/'.dsh-state/parameter-cache'
    folder=project/'milestones/reproducibility/parameter-evidence'
    index_path=folder/'lindab-document-index.json'
    index=json.loads(index_path.read_text(encoding='utf-8'))
    duct=next(r for r in index['documents'] if 'SR' in r['products_from_official_rows'])
    fitting=next(r for r in index['documents'] if 'BFU' in r['products_from_official_rows'])
    stem=Path(duct['filename']).stem
    text_path=cache/(stem+'_page15.txt')
    word_path=cache/(stem+'_page15_words.json')
    rows=parse_weights(text_path.read_text(encoding='utf-8'),json.loads(word_path.read_text(encoding='utf-8')))
    duct_summary=(cache/(stem+'_page03.txt')).read_text(encoding='utf-8')
    if '1 kg of circular ventilation duct' not in duct_summary:
        raise ValueError('Duct declared unit missing')
    total=summary_factor(duct_summary,'total')
    fossil=summary_factor(duct_summary,'fossil')
    module_text=(cache/(stem+'_page11.txt')).read_text(encoding='utf-8')
    for metric,value in [('TOTAL1)',total),('FOSSIL',fossil)]:
        line=next(line for line in module_text.splitlines() if 'GWP' in line and metric in line)
        cells=re.findall(r'[+-]?\d+,\d+E[+\-]\d+|MND|MNR',line.replace('‐','-'))
        if len(cells)!=18 or abs(float(cells[3].replace(',','.'))-value)>1e-12:
            raise ValueError('Module-row A1-A3 differs from summary')
    for row in rows:
        row['reference_A1_A3_GWP_total_kgCO2e_per_m']=row['mass_kg_per_m']*total
        row['reference_A1_A3_GWP_fossil_kgCO2e_per_m']=row['mass_kg_per_m']*fossil
        row['status']='REFERENCE_CATALOGUE_ONLY; not_actual_BIM_mass_or_carbon'
    fitting_path=cache/(Path(fitting['filename']).stem+'_page03.txt')
    fitting_summary=fitting_path.read_text(encoding='utf-8')
    coverage=[]
    hashes={index_path.name:sha(index_path),text_path.name:sha(text_path),word_path.name:sha(word_path)}
    for material in ['concrete','timber']:
        path=project/'milestones/reproducibility/network-interfaces'/(material+'-interfaces.json')
        hashes[path.name]=sha(path)
        model=json.loads(path.read_text(encoding='utf-8'))
        diameters={r['diameter_mm'] for r in rows}
        pipes=[r for r in model['components'] if r['ifc_type']=='IfcDuctSegment']
        matched=[]
        unmatched=[]
        for pipe in pipes:
            raw=pipe.get('psets',{}).get('FI_Geometria',{}).get('Halkaisija')
            if isinstance(raw,(int,float)) and raw in diameters:
                matched.append(pipe['ifc_id'])
            else:
                unmatched.append({'ifc_id':pipe['ifc_id'],'raw_diameter':raw})
        coverage.append({'model_id':model['model_id'],'pipe_count':len(pipes),'catalogue_nominal_size_matched':len(matched),
            'unmatched':unmatched,'scope':'Diameter compatibility only; manufacturer and actual mass are not certified.'})
    sources=[cache/duct['filename'],cache/fitting['filename'],cache/(stem+'_page03.txt'),cache/(stem+'_page11.txt'),cache/(stem+'_page01.txt'),fitting_path]
    hashes.update({p.name:sha(p) for p in sources})
    result={'artifact_type':'source_qualified_reference_duct_catalogue','status':'REFERENCE_PARAMETERS_AVAILABLE_PROTOCOL_PENDING',
        'inputHashes':hashes,'codeSha256':sha(Path(__file__)),'duct_epd':duct['url'],'fitting_epd':fitting['url'],
        'declared_unit':'1 kg circular duct','duct_A1_A3_GWP_total_kgCO2e_per_kg':total,
        'duct_A1_A3_GWP_fossil_kgCO2e_per_kg':fossil,'catalogue':rows,'nominal_size_coverage':coverage,
        'fitting_summary':{'declared_unit':'1 kg fitting product','A1_A3_GWP_total':summary_factor(fitting_summary,'total'),
            'A1_A3_GWP_fossil':summary_factor(fitting_summary,'fossil'),'status':'Summary source only; fitting mass/type applicability pending.'},
        'limitations':['Annex weights are explicitly representative standard sizes; do not claim exact installed product masses.',
            'Generic FeZn BIM cannot identify Lindab as actual supplier; use only an explicitly approved reference-product scenario.',
            'Duct EPD published 2024 and revised 2025; do not silently call revised document a 2024 original.',
            'D credits have trailing-minus extraction ambiguity; do not assign module D values from this text.',
            'No prices, pressure coefficients, replacement, hours, tariffs or grid factors assigned.',
            'No whole-network emissions or optimization comparison computed.']}
    (folder/'lindab-reference-catalogue.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':result['status'],'catalogue_size':len(rows),'duct_GWP_total':total,'duct_GWP_fossil':fossil,
        'examples':[r for r in rows if r['diameter_mm'] in (160,315)],'nominal_size_coverage':coverage,
        'fitting_summary':result['fitting_summary']},ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
