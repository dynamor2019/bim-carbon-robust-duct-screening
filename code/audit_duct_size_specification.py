"""Native typed duct dimensions and conditional specification-band screening."""
import json,math
from collections import Counter
from pathlib import Path
import ifcopenshell
from guard_engineering_inputs import sha
from resolve_ifc_units import resolve_property


def band(size_mm,shape):
    if type(size_mm) not in (int,float) or not math.isfinite(size_mm) or size_mm<=0:
        return None
    ranges=[(100,315,.5),(400,800,.7),(1000,1250,.9)] if shape=='CIRCULAR' else ([(0,250,.5),(300,800,.7),(1000,float('inf'),.9)] if shape=='RECTANGULAR' else [])
    matches=[t for lo,hi,t in ranges if lo<=size_mm<=hi]
    return matches[0] if len(matches)==1 else None


def main():
    project=Path(__file__).resolve().parents[1]
    materials=project/'milestones/reproducibility/native-duct-material-audit.json'
    specification=project/'milestones/reproducibility/duct-material-table-audit.json'
    material_data=json.loads(materials.read_text(encoding='utf-8'))
    spec=json.loads(specification.read_text(encoding='utf-8'))
    expected=[.5,.7,.9,.5,.7,.9,1.25]
    if spec['status']!='PASS_SOURCE_TABLE_PAIRING_ONLY' or [r['wall_thickness_mm'] for r in spec['rows']]!=expected:
        raise ValueError('Specification transcription changed; revise bounded screening')
    sources=[{'path':str(p),'sha256':sha(p)} for p in (materials,specification)]
    reports=[]
    for model_record,source_record in zip(material_data['models'],material_data['source_files']):
        path=Path(source_record['path']); before=sha(path)
        if before!=source_record['sha256']: raise ValueError('Stale original material source')
        print('Audit typed dimensions:',model_record['variant'],flush=True)
        model=ifcopenshell.open(path)
        projects=model.by_type('IfcProject')
        if len(projects)!=1: raise ValueError('Ambiguous project unit context')
        units=[u.get_info(recursive=True) for u in projects[0].UnitsInContext.Units]
        rows=[]
        for record in model_record['rows']:
            entity=model.by_id(record['ifc_id']); properties={}
            for relation in entity.IsDefinedBy:
                if not relation.is_a('IfcRelDefinesByProperties'): continue
                pset=relation.RelatingPropertyDefinition
                if not pset.is_a('IfcPropertySet') or pset.Name!='FI_Geometria': continue
                for p in pset.HasProperties:
                    if not p.is_a('IfcPropertySingleValue') or p.Name not in ('Halkaisija','Korkeus','Leveys','Koko (DU)'): continue
                    if p.Name in properties: raise ValueError('Duplicate geometry property')
                    v=p.NominalValue
                    meta={'property_id':p.id(),'nominal_value_type':v.is_a() if v else None,'raw_value':v.wrappedValue if v else None,'explicit_unit':p.Unit.get_info(recursive=True) if p.Unit else None}
                    meta['resolved_unit']=resolve_property(meta,units)
                    meta['value_mm']=meta['raw_value']*meta['resolved_unit']['scale_to_SI']*1000 if meta['resolved_unit'] and type(meta['raw_value']) in (int,float) else None
                    properties[p.Name]=meta
            values={k:v['value_mm'] for k,v in properties.items()}
            d,h,w=(values.get(k) for k in ('Halkaisija','Korkeus','Leveys'))
            positive=lambda x:type(x) in (int,float) and math.isfinite(x) and x>0
            shape='CIRCULAR' if positive(d) and h==0 and w==0 else ('RECTANGULAR' if d==0 and positive(h) and positive(w) else 'UNRESOLVED')
            size=d if shape=='CIRCULAR' else (max(h,w) if shape=='RECTANGULAR' else None)
            thickness=band(size,shape)
            rows.append({'ifc_id':entity.id(),'guid':entity.GlobalId,'properties':properties,'shape':shape,'screen_size_mm':size,
                'conditional_spec_thickness_mm':thickness,'status':'CONDITIONAL_BAND_MATCH' if thickness else 'UNRESOLVED_OR_UNCOVERED',
                'engineering_adopted':False,'conditions':['Specification size-label units must be confirmed as mm.','Ordinary galvanized category applicability and actual construction must be qualified.']})
        if sha(path)!=before: raise ValueError('Original IFC changed')
        sources.append({'path':str(path),'sha256':before})
        reports.append({'variant':model_record['variant'],'counts':dict(Counter(r['status'] for r in rows)),'shape_counts':dict(Counter(r['shape'] for r in rows)),'rows':rows})
    report={'artifact_type':'typed_duct_size_conditional_specification_screen','status':'CONDITIONAL_SPECIFICATION_SCREEN_ONLY','codeSha256':sha(Path(__file__)),
        'helperHashes':{name:sha(Path(__file__).with_name(name)) for name in ('resolve_ifc_units.py','guard_engineering_inputs.py')},
        'source_files':sources,'models':reports,'no_gap_interpolation':True,'mass_calculated':False,'formal_experiment':False}
    (project/'milestones/reproducibility/duct-size-specification-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='')
    print(json.dumps([{'variant':r['variant'],'counts':r['counts'],'shape_counts':r['shape_counts']} for r in reports],indent=2))

if __name__=='__main__': main()
