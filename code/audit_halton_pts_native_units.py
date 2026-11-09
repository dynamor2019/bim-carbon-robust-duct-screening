"""Read raw IFC PTS technical properties; do not infer angle or loss curves."""
import json,gc
from pathlib import Path
from collections import Counter
import ifcopenshell
from guard_engineering_inputs import sha
from resolve_ifc_units import resolve_property

FIELDS=('Esisäätöarvo, laskettu','Painehäviö','Kokonaispaine','Virtaama','Virtausnopeus')

def unit_evidence(meta,units):
    if meta['nominal_value_type']=='IfcPressureMeasure':
        choices=[meta['explicit_unit']] if meta['explicit_unit'] else [u for u in units if u.get('UnitType')=='PRESSUREUNIT']
        if len(choices)!=1: raise ValueError('Pressure unit absent/ambiguous')
        u=choices[0]
        if u['type']!='IfcSIUnit' or u.get('Name')!='PASCAL' or u.get('Prefix') is not None: raise ValueError('Pressure unit unsupported; preserve rather than guess')
        return {'unit_type':'PRESSUREUNIT','scale_to_SI':1.0,'SI_unit':'Pa','basis':'PROPERTY_OVERRIDE' if meta['explicit_unit'] else 'TYPED_PROJECT_UNIT_INHERITANCE'}
    return resolve_property(meta,units)

if __name__=='__main__':
    project=Path(__file__).resolve().parents[1]; root=project/'milestones/reproducibility'; inp=root/'halton-pts-source-review.json'; data=json.loads(inp.read_text(encoding='utf-8'));sources=[{'path':str(inp),'sha256':sha(inp)}];models=[]
    for record in data['models']:
        path=project.parent/f"extracted/HVAC/IFC/HVAC_NordicLCA_Office_{record['variant'].title()}_BuildingPermit.ifc"; before=sha(path)
        print('Read native PTS fields:',record['variant'],flush=True);model=ifcopenshell.open(path)
        projects=model.by_type('IfcProject')
        if len(projects)!=1: raise ValueError('Project unit context ambiguous')
        units=[u.get_info(recursive=True) for u in projects[0].UnitsInContext.Units];rows=[]
        for cached in record['objects']:
            obj=model.by_id(cached['ifc_id'])
            if obj.GlobalId!=cached['guid'] or obj.Name!=cached['name']: raise ValueError('Object identity differs')
            props={}
            for rel in obj.IsDefinedBy:
                if not rel.is_a('IfcRelDefinesByProperties'): continue
                ps=rel.RelatingPropertyDefinition
                if not ps.is_a('IfcPropertySet') or ps.Name!='FI_Tekninen':continue
                for p in ps.HasProperties:
                    if not p.is_a('IfcPropertySingleValue') or p.Name not in FIELDS:continue
                    if p.Name in props: raise ValueError('Duplicate property')
                    v=p.NominalValue;meta={'property_id':p.id(),'nominal_value_type':v.is_a() if v is not None else None,'raw_value':v.wrappedValue if v is not None else None,'explicit_unit':p.Unit.get_info(recursive=True) if p.Unit else None}
                    if meta['raw_value']!=cached['technical_fields_native'].get(p.Name):raise ValueError('Cached field differs from raw')
                    meta['resolved_unit']=unit_evidence(meta,units)
                    meta['value_SI']=meta['raw_value']*meta['resolved_unit']['scale_to_SI'] if meta['resolved_unit'] is not None and type(meta['raw_value']) in (float,int) else None
                    props[p.Name]=meta
            if set(props)!=set(FIELDS):raise ValueError('PTS technical field coverage missing')
            rows.append({'ifc_id':obj.id(),'guid':obj.GlobalId,'name':obj.Name,'properties':props})
        counts={field:dict(Counter(r['properties'][field]['nominal_value_type'] for r in rows)) for field in FIELDS}
        models.append({'variant':record['variant'],'object_count':len(rows),'measure_type_counts':counts,'project_units':units,'rows':rows});sources.append({'path':str(path),'sha256':before})
        if sha(path)!=before:raise ValueError('Source changed')
        del model,projects,obj,rel,ps,p,v;gc.collect()
    out={'artifact_type':'PTS_raw_IFC_technical_unit_audit','status':'PASS_RAW_CACHE_UNIT_AUDIT_ONLY','codeSha256':sha(Path(__file__)),'helperHashes':{'resolve_ifc_units.py':sha(Path(__file__).with_name('resolve_ifc_units.py'))},'source_files':sources,'models':models,'formal_experiment':False,'limits':['Unit scale verification is not pressure basis or source design calculation certification.','Unresolved nominal types receive no inferred angle/percent meaning.','Raw/cache agreement is not independent engineering recomputation.','No loss coefficient or candidate flow pressure curve adopted.']}
    (root/'halton-pts-native-unit-audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':out['status'],'models':[{k:v for k,v in r.items() if k not in ('rows','project_units')} for r in models]},ensure_ascii=False,indent=2))
