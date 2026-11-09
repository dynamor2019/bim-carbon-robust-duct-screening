"""Verify native typed flow units and nominal Q=vA consistency.
Internal source consistency is not independent measured-flow validation.
"""
import csv
import json
import math
import statistics
from pathlib import Path
from recover_fitting_interfaces import sha


def positive(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>0


def nominal_area(geometry):
    diameter=geometry.get('Halkaisija')
    width=geometry.get('Leveys')
    height=geometry.get('Korkeus')
    circle=positive(diameter)
    rectangle=positive(width) and positive(height)
    if circle==rectangle:
        return None
    return (math.pi*(diameter/1000)**2/4,'CIRCULAR_NOMINAL_MM') if circle else (width*height/1e6,'RECTANGULAR_NOMINAL_MM')


def main():
    project=Path(__file__).resolve().parents[1]
    folder=project/'milestones/reproducibility/network-interfaces'
    models=[]
    unit_path=folder/'native-property-unit-review.json'
    unit_review=json.loads(unit_path.read_text(encoding='utf-8'))
    if unit_review['status']!='PASS_TYPED_UNIT_RESOLUTION':
        raise ValueError('Native typed unit resolution has not passed')
    unit_models={m['model_id']:m for m in unit_review['models']}
    hashes={unit_path.name:sha(unit_path)}
    documentation=project/'.dsh-state/parameter-cache/buildingsmart-property-single-value.md'
    hashes[documentation.name]=sha(documentation)
    all_rows=[]
    for material in ['concrete','timber']:
        path=folder/(material+'-interfaces.json')
        hashes[path.name]=sha(path)
        data=json.loads(path.read_text(encoding='utf-8'))
        unit_model=unit_models[data['model_id']]
        if unit_review['inputHashes'][path.name]!=hashes[path.name]:
            raise ValueError('Native unit audit binds stale inventory')
        native={row['ifc_id']:row for row in unit_model['rows']}
        rows=[]
        for record in data['components']:
            if record['ifc_type']!='IfcDuctSegment':
                continue
            technical=record['psets'].get('FI_Tekninen',{})
            flow=technical.get('Virtaama')
            velocity=technical.get('Virtausnopeus')
            metadata=native[record['ifc_id']]['properties']
            if metadata['Virtaama']['raw_value']!=flow or metadata['Virtausnopeus']['raw_value']!=velocity:
                raise ValueError('Cached flow/velocity differs from original native IFC audit')
            flow_scale=metadata['Virtaama']['resolved_unit']['scale_to_SI']
            velocity_scale=metadata['Virtausnopeus']['resolved_unit']['scale_to_SI']
            area=nominal_area(record['psets'].get('FI_Geometria',{}))
            row={'model_id':data['model_id'],'ifc_id':record['ifc_id'],'guid':record['guid'],'name':record['name'],
                'raw_flow':flow,'raw_velocity':velocity,'nominal_area_m2':area[0] if area else None,'section_basis':area[1] if area else None,
                'raw_flow_over_vA':None,'L_s_relative_residual':None,'m3_h_relative_residual':None,'m3_s_relative_residual':None,
                'native_SI_relative_residual':None,'source_flow_unit_scale_to_m3_s':flow_scale,'source_velocity_unit_scale_to_m_s':velocity_scale,
                'status':'NOT_EVALUATED_MISSING_NONPOSITIVE_OR_AMBIGUOUS; raw_values_retained'}
            if area and positive(flow) and positive(velocity):
                reference=velocity*velocity_scale*area[0]
                row['raw_flow_over_vA']=flow/reference
                row['native_SI_relative_residual']=(flow*flow_scale-reference)/reference
                for key,scale in [('L_s',1000),('m3_h',3600),('m3_s',1)]:
                    row[key+'_relative_residual']=(flow/scale-reference)/reference
                row['status']='TYPED_INHERITED_UNITS_VERIFIED; nominal_area_consistency_only'
            rows.append(row)
        evaluated=[r for r in rows if r['raw_flow_over_vA'] is not None]
        summary={'pipe_count':len(rows),'evaluated_count':len(evaluated),'retained_not_evaluated':len(rows)-len(evaluated)}
        for key in ['raw_flow_over_vA','native_SI_relative_residual','L_s_relative_residual','m3_h_relative_residual','m3_s_relative_residual']:
            values=[r[key] for r in evaluated]
            summary[key]={'minimum':min(values),'median':statistics.median(values),'maximum':max(values)} if values else None
        for key in ['L_s','m3_h','m3_s']:
            summary[key+'_within_1pct']=sum(abs(r[key+'_relative_residual'])<=.01 for r in evaluated)
        models.append({'model_id':data['model_id'],'summary':summary,'rows':rows})
        all_rows.extend(rows)
    result={'artifact_type':'typed_unit_source_flow_velocity_consistency','status':'SOURCE_INTERNAL_CONSISTENCY_ONLY',
        'inputHashes':hashes,'codeSha256':sha(Path(__file__)),'models':models,
        'limitations':['Flow and velocity units resolved from native typed measures and project context; explicit property unit overrides audited.',
            'Source flow/speed may be generated by the same design calculator, so agreement is not independent measured evidence.',
            'Nominal area excludes unverified wall thickness, local obstruction and actual free area.',
            '1% is an exploratory screen, not an engineering acceptance limit.',
            'No nonpositive/missing value filled, no terminal rescaled, no result unit field overwritten.']}
    (folder/'flow-unit-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    with (folder/'flow-unit-review.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(all_rows[0]),lineterminator='\n')
        writer.writeheader()
        writer.writerows(all_rows)
    print(json.dumps([{'model_id':m['model_id'],'summary':m['summary']} for m in models],indent=2))


if __name__=='__main__':
    main()
