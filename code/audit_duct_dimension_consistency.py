"""Cross-check source labels and typed dimensions; no independent physical measurement."""
import json,re,math
from collections import Counter
from pathlib import Path
from guard_engineering_inputs import sha


def check(row):
    props=row['properties']; label=props.get('Koko (DU)',{}).get('raw_value')
    values={k:props.get(k,{}).get('value_mm') for k in ('Halkaisija','Leveys','Korkeus')}
    violations=[{'field':k,'property_id':p.get('property_id'),'type':p['nominal_value_type'],'raw_value':p.get('raw_value')}
        for k,p in props.items() if p.get('nominal_value_type')=='IfcPositiveLengthMeasure' and type(p.get('raw_value')) in (int,float) and p['raw_value']<=0]
    parsed=None; match=False
    if isinstance(label,str):
        circle=re.fullmatch(r'Ø(\d+(?:[.,]\d+)?)',label.strip())
        rectangle=re.fullmatch(r'(\d+(?:[.,]\d+)?)x(\d+(?:[.,]\d+)?)',label.strip())
        if circle and row['shape']=='CIRCULAR':
            parsed=[float(circle.group(1).replace(',','.'))]
            actual=values['Halkaisija']
            match=type(actual) in (int,float) and math.isfinite(actual) and abs(actual-parsed[0])<=1e-8
        elif rectangle and row['shape']=='RECTANGULAR':
            parsed=[float(x.replace(',','.')) for x in rectangle.groups()]
            actual=[values['Leveys'],values['Korkeus']]
            # Preserve orientation: label width x height; do not reorder to make it fit.
            match=all(type(a) in (int,float) and math.isfinite(a) and abs(a-b)<=1e-8 for a,b in zip(actual,parsed))
    return {'ifc_id':row['ifc_id'],'guid':row['guid'],'shape':row['shape'],'label':label,'typed_dimensions_mm':values,
        'parsed_label_numbers':parsed,'status':'PASS_LABEL_NUMERIC_AGREEMENT_CONDITIONAL_MM' if match else 'UNRESOLVED_OR_MISMATCH',
        'positive_measure_domain_violations':violations,'engineering_adopted':False}


def main():
    project=Path(__file__).resolve().parents[1]
    source=project/'milestones/reproducibility/duct-size-specification-audit.json'; before=sha(source)
    data=json.loads(source.read_text(encoding='utf-8'))
    for bound in data['source_files']:
        if sha(Path(bound['path']))!=bound['sha256']: raise ValueError('Stale upstream source binding')
    reports=[]
    for model in data['models']:
        rows=[check(r) for r in model['rows']]
        if not rows or len({r['guid'] for r in rows})!=len(rows): raise ValueError('Empty/duplicate source object identities')
        reports.append({'variant':model['variant'],'counts':dict(Counter(r['status'] for r in rows)),
            'objects_with_positive_measure_domain_violations':sum(bool(r['positive_measure_domain_violations']) for r in rows),
            'positive_measure_domain_violation_count':sum(len(r['positive_measure_domain_violations']) for r in rows),'rows':rows})
    if sha(source)!=before: raise ValueError('Upstream result changed during audit')
    report={'artifact_type':'duct_source_label_numeric_and_type_domain_audit','status':'SOURCE_LABEL_CROSSCHECK_WITH_DOMAIN_FINDINGS',
        'codeSha256':sha(Path(__file__)),'helperHashes':{'guard_engineering_inputs.py':sha(Path(__file__).with_name('guard_engineering_inputs.py'))},
        'source_files':[{'path':str(source),'sha256':before}]+data['source_files'],'models':reports,
        'numeric_tolerance_mm':1e-8,'limitations':['Label unit assumed mm only for conditional comparison; text agreement does not independently establish units.',
            'Both fields originate in one model; not independent recomputation/measurement or installed dimension verification.',
            'Positive length zero/negative values remain schema domain findings, never repaired or adopted as engineering data.'],
        'formal_experiment':False}
    (project/'milestones/reproducibility/duct-dimension-consistency-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='')
    print(json.dumps([{k:v for k,v in m.items() if k!='rows'} for m in reports],indent=2))

if __name__=='__main__': main()
