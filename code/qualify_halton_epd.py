"""Qualify EPD text/word table extraction without adopting optimization factors."""
import json
import re
from datetime import datetime
from pathlib import Path
from recover_fitting_interfaces import sha

MODULES=['A1','A2','A3','A1-A3','A4','A5','B1','B2','B3','B4','B5','B6','B7','C1','C2','C3','C4','D']
METRICS={'GWP-total':'total1)','GWP-fossil':'fossil','GWP-biogenic':'biogenic','GWP-LULUC':'LULUC'}


def normalize(value):
    for character in ('‐','−','–','‑'):
        value=value.replace(character,'-')
    return value


def cell(token):
    token=normalize(token)
    if token in ('MND','MNR'):
        return {'raw':token,'value':None,'state':'NOT_DECLARED' if token=='MND' else 'NOT_RELEVANT','rounding_half_unit':None}
    if not re.fullmatch(r'[+-]?\d+,\d+E[+-]\d+',token):
        raise ValueError('Unexpected EPD numeric token: '+token)
    mantissa,exponent=token.split('E')
    half=.5*10**(int(exponent)-len(mantissa.split(',')[1]))
    return {'raw':token,'value':float(token.replace(',','.')),'state':'DECLARED','rounding_half_unit':half}


def tables(text,words):
    lines=text.splitlines()
    text_rows={}
    for metric,label in METRICS.items():
        index=next(i for i,line in enumerate(lines) if 'GWP' in line and label in line)
        values=lines[index+1].split()
        if len(values)!=len(MODULES):
            raise ValueError('Unexpected EPD row column count')
        text_rows[metric]={module:cell(value) for module,value in zip(MODULES,values)}
    header={}
    for module in MODULES:
        found=[w for w in words if normalize(w[4])==module]
        if len(found)!=1:
            raise ValueError('Ambiguous module header: '+module)
        header[module]=(found[0][0]+found[0][2])/2
    clusters=[]
    for word in sorted(words,key=lambda w:(w[1]+w[3])/2):
        token=normalize(word[4])
        if token not in ('MND','MNR') and not re.fullmatch(r'[+-]?\d+,\d+E[+-]\d+',token):
            continue
        y=(word[1]+word[3])/2
        for cluster in clusters:
            if abs(y-cluster['y'])<=2:
                cluster['words'].append(word)
                break
        else:
            clusters.append({'y':y,'words':[word]})
    clusters=[c for c in clusters if len(c['words'])==len(MODULES)]
    word_rows={}
    for metric,label in METRICS.items():
        found=[w for w in words if w[4]==label]
        if len(found)!=1:
            raise ValueError('Ambiguous GWP row label: '+label)
        y=(found[0][1]+found[0][3])/2
        cluster=min(clusters,key=lambda c:abs(c['y']-y))
        if abs(cluster['y']-y)>15:
            raise ValueError('EPD row label not aligned with numeric row')
        row={}
        for word in cluster['words']:
            x=(word[0]+word[2])/2
            module=min(MODULES,key=lambda m:abs(x-header[m]))
            if module in row:
                raise ValueError('Multiple words assigned to one module')
            row[module]=cell(word[4])
        if set(row)!=set(MODULES):
            raise ValueError('Missing module assignment')
        word_rows[metric]=row
    if text_rows!=word_rows:
        raise ValueError('Text-line and coordinate-based EPD table extraction disagree')
    checks=[]
    for metric,row in text_rows.items():
        parts=[row[m] for m in ['A1','A2','A3']]
        difference=sum(p['value'] for p in parts)-row['A1-A3']['value']
        bound=sum(p['rounding_half_unit'] for p in parts)+row['A1-A3']['rounding_half_unit']
        checks.append({'metric':metric,'A1_plus_A2_plus_A3_minus_reported_total':difference,
            'rounding_bound':bound,'pass':abs(difference)<=bound+1e-12})
    if not all(c['pass'] for c in checks):
        raise ValueError('EPD module sum fails printed precision bound')
    return text_rows,checks


def main():
    project=Path(__file__).resolve().parents[1]
    cache=project/'.dsh-state/parameter-cache'
    prefix='Halton_URH_ULA_EPD_HUB-1432'
    text_path=cache/(prefix+'_page07.txt')
    words_path=cache/(prefix+'_page07_words.json')
    rows,checks=tables(text_path.read_text(encoding='utf-8'),json.loads(words_path.read_text(encoding='utf-8')))
    page2=(cache/(prefix+'_page02.txt')).read_text(encoding='utf-8')
    page3=(cache/(prefix+'_page03.txt')).read_text(encoding='utf-8')
    page1=(cache/(prefix+'_page01.txt')).read_text(encoding='utf-8')
    required=['URH/A-125','1 kg','Multiple products','EN 15804+A2:2019']
    if not all(s in page2 for s in required) or '25 years' not in page3 or '23.05.2024' not in page1:
        raise ValueError('EPD scope/version/declared unit evidence changed')
    dates=re.search(r'Published on (\d{2}\.\d{2}\.\d{4}), last updated on (\d{2}\.\d{2}\.\d{4}), valid until (\d{2}\.\d{2}\.\d{4})',page1)
    if dates is None:
        raise ValueError('EPD dates not parsed unambiguously')
    publication,updated,expiry=[datetime.strptime(d,'%d.%m.%Y').date().isoformat() for d in dates.groups()]
    mass=float(re.search(r'Declared unit\s+(\d+(?:[.,]\d+)?)\s+kg',page2).group(1).replace(',','.'))
    product_reference=re.search(r'Product reference\s+(URH/[A-Z]-\d+)',page2).group(1)
    rsl=int(re.search(r'Reference service life\s+(\d+) years',page3).group(1))
    production_year=int(re.search(r'Calendar year,\s*(\d{4})',page2).group(1))
    page6=(cache/(prefix+'_page06.txt')).read_text(encoding='utf-8')
    if 'The EPD averages two products: Halton URH and ULA' not in page6:
        raise ValueError('EPD averaged product family statement missing')
    sources=[cache/(prefix+'.pdf'),text_path,words_path]+[cache/(prefix+f'_page{i:02d}.txt') for i in [1,2,3,4,6]]
    result={'artifact_type':'manufacturer_epd_qualified_candidate','status':'SOURCE_TABLE_VERIFIED_APPLICABILITY_PENDING',
        'pdf_source_url':'https://media.halton.com/app/uploads/2025/02/Halton_supply_exhaust_valves_URH_ULA_EPD_HUB-1432.pdf',
        'sourceHashes':{p.name:sha(p) for p in sources},'codeSha256':sha(Path(__file__)),
        'declared_unit':{'mass_kg':mass,'basis':'kg product; not one terminal'},
        'product_reference':product_reference,'averaging':'Multiple products; representative product weighted by total units produced',
        'averaged_product_families':['Halton URH','Halton ULA'],'family_scope':'Different sizes explicitly included; factor is family representative, not size-specific.',
        'production_data_year':production_year,
        'publication_date':publication,'last_updated':updated,'valid_until':expiry,
        'reference_service_life_years':rsl,'RSL_scope':'Product assumption; not duct lifespan, study period or replacement schedule.',
        'functional_unit_scope':'Reference URH/A-125 airflow 18 m3/h, 24/7; not office operating hours.',
        'units':'kg CO2e per declared 1 kg','GWP_module_cells':rows,'printed_rounding_checks':checks,
        'column_alignment_status':'Text and independent word-coordinate assignments agree; no rendered visual QA claimed.',
        'source_locations':{'unit_product_scope':'physical page 2','product_RSL_packaging_carbon':'physical page 3',
            'life_cycle_boundary':'physical page 4','GWP_modules':'physical page 7'},
        'boundary_warning':'A3 biogenic negative value and A5 positive release are both retained. A1-A3-only GWP-total is a partial-module indicator; cannot label it complete whole-life carbon.',
        'adoption_decision':'NO_OPTIMIZATION_FACTOR_ASSIGNED',
        'remaining_checks':['Family representative-factor use must be specified in the protocol; match mass source and size, without claiming size-specific factor.',
            'Replacement modelling must define B4 separately; B4 MND is not zero.',
            'B6 MND/passive valve is not zero fan electricity.',
            'Does not supply duct, fitting, damper, silencer, AHU or cost factors.',
            'Frozen selected-module protocol needs explicit boundary review before formal use.']}
    output=project/'milestones/reproducibility/parameter-evidence/halton-epd-review.json'
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':result['status'],'declared_unit':result['declared_unit'],
        'product_reference':result['product_reference'],
        'A1-A3_GWP':{k:v['A1-A3'] for k,v in rows.items()},
        'B4_B6_status':{k:rows['GWP-total'][k] for k in ['B4','B6']},
        'printed_rounding_checks':checks},ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
