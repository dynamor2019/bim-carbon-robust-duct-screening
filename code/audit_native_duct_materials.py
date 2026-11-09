"""Audit explicit native duct material evidence; group membership is not connectivity."""
import json,re
from pathlib import Path
import ifcopenshell
import ifcopenshell.util.element
from guard_engineering_inputs import sha

PATTERN=re.compile(r'material|materiaali|thickness|paksuus|wall',re.I)


def plain(value):
    if isinstance(value,ifcopenshell.entity_instance):
        return {'ifc_id':value.id(),'ifc_class':value.is_a(),'name':getattr(value,'Name',None)}
    if isinstance(value,(tuple,list)):
        return [plain(v) for v in value]
    if isinstance(value,dict):
        return {k:plain(v) for k,v in value.items()}
    return value


def layers(material):
    if material is None: return []
    if material.is_a('IfcMaterialLayerSetUsage'): material=material.ForLayerSet
    if material.is_a('IfcMaterialLayerSet'):
        return [{'layer_id':l.id(),'material':plain(l.Material),'layer_thickness_native':l.LayerThickness} for l in material.MaterialLayers]
    if material.is_a('IfcMaterialLayer'):
        return [{'layer_id':material.id(),'material':plain(material.Material),'layer_thickness_native':material.LayerThickness}]
    return []


def main():
    project=Path(__file__).resolve().parents[1]
    reports=[]
    sources=[]
    for variant in ('Concrete','Timber'):
        source=project.parent/f'extracted/HVAC/IFC/HVAC_NordicLCA_Office_{variant}_BuildingPermit.ifc'
        before=sha(source); model=ifcopenshell.open(source)
        groups=[g for g in model.by_type('IfcDistributionSystem') if getattr(g,'Name',None)=='302PK01 (toimistot, oikea)']
        if len(groups)!=1:
            raise ValueError('Exact native full system assignment missing or ambiguous')
        ids=set()
        for g in groups:
            for relation in getattr(g,'IsGroupedBy',[]):
                ids.update(o.id() for o in relation.RelatedObjects)
        rows=[]
        for id_ in sorted(ids):
            obj=model.by_id(id_)
            if not obj.is_a('IfcFlowSegment'): continue
            mat=ifcopenshell.util.element.get_material(obj,should_skip_usage=False,should_inherit=True)
            direct=[r for r in getattr(obj,'HasAssociations',[]) if r.is_a('IfcRelAssociatesMaterial')]
            psets=ifcopenshell.util.element.get_psets(obj)
            matches=[{'pset':ps,'field':key,'value':plain(value)} for ps,values in psets.items() for key,value in values.items() if key!='id' and PATTERN.search(key)]
            rows.append({'ifc_id':id_,'guid':obj.GlobalId,'name':obj.Name,'ifc_class':obj.is_a(),
                'material_with_inheritance':plain(mat),'direct_material_associations':[r.id() for r in direct],
                'layers':layers(mat),'matched_properties':matches})
        if not rows:
            raise ValueError('Zero flow segment sample cannot establish material coverage')
        if sha(source)!=before: raise ValueError('Source hash changed during audit')
        sources.append({'path':str(source),'sha256':before})
        reports.append({'variant':variant,'matching_groups':[g.id() for g in groups],'native_member_ids_count':len(ids),
            'flow_segments_count':len(rows),'material_assigned_count':sum(r['material_with_inheritance'] is not None for r in rows),
            'layer_evidence_count':sum(bool(r['layers']) for r in rows),'property_evidence_count':sum(bool(r['matched_properties']) for r in rows),'rows':rows})
    report={'artifact_type':'native_302PK01_flow_segment_material_evidence','status':'SOURCE_MATERIAL_AUDIT_ONLY','codeSha256':sha(Path(__file__)),
        'helperHashes':{'guard_engineering_inputs.py':sha(Path(__file__).with_name('guard_engineering_inputs.py'))},'source_files':sources,'models':reports,
        'limitations':['IfcFlowSegment inclusion follows native named group, not certified physical service.',
            'Property name search is bounded, may include unrelated width/insulation fields or miss uncommon names.',
            'LayerThickness remains native length unit, no implicit SI conversion or shell-mass calculation.',
            'Material names do not certify manufacturer EPD or installed construction.']}
    target=project/'milestones/reproducibility/native-duct-material-audit.json'
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':report['status'],'models':[{k:v for k,v in r.items() if k!='rows'} for r in reports]},indent=2))

if __name__=='__main__': main()
