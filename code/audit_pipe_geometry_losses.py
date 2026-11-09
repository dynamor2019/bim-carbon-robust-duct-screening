"""Screen source straight-pipe geometry against source length and pressure-gradient fields.
Effective loss length is a diagnostic, not proof of a stale design or friction-only loss.
"""
import csv
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def numeric(value):
    return float(value) if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) else None


def main():
    project=Path(__file__).resolve().parents[1]
    folder=project/'milestones/reproducibility/network-interfaces'
    rows=[]
    reports=[]
    hashes={}
    for material in ['concrete','timber']:
        path=folder/(material+'-interfaces.json')
        hashes[path.name]=sha(path)
        data=json.loads(path.read_text(encoding='utf-8'))
        reasons=Counter()
        ratios=[]
        property_errors=[]
        examples=[]
        for record in data['components']:
            if record['ifc_type']!='IfcDuctSegment':
                continue
            axes=record.get('axes',[])
            geometry=record.get('psets',{}).get('FI_Geometria',{})
            tech=record.get('psets',{}).get('FI_Tekninen',{})
            prop_length=numeric(geometry.get('Pituus'))
            loss=numeric(tech.get('Painehäviö'))
            gradient=numeric(tech.get('Painehäviö per metri'))
            length=axes[0]['axis_length_m'] if len(axes)==1 else None
            effective_length=None
            ratio=None
            prop_error=None
            if length is None or length<=0:
                status='NO_SINGLE_POSITIVE_EXTRUSION_AXIS'
            elif loss is None or gradient is None:
                status='LOSS_OR_GRADIENT_MISSING'
            elif loss<=0 or gradient<=0:
                status='LOSS_OR_GRADIENT_NONPOSITIVE_NOT_IMPUTED'
            else:
                effective_length=loss/gradient
                ratio=effective_length/length
                ratios.append(ratio)
                status='EVALUATED_SOURCE_LENGTH_DEFINITIONS_UNVERIFIED'
            if length and prop_length is not None:
                prop_error=abs(prop_length/1000-length)/length
                property_errors.append(prop_error)
            reasons[status]+=1
            row={'model_id':data['model_id'],'ifc_id':record['ifc_id'],'guid':record['guid'],
                'source_axis_length_m':length,'raw_Pituus':prop_length,'Pituus_mm_candidate_relative_error':prop_error,
                'raw_pressure_loss':loss,'raw_pressure_loss_per_metre':gradient,
                'effective_loss_length_candidate_m':effective_length,'effective_to_axis_length_ratio':ratio,
                'status':status,'limitation':'No source unit/length definition or pressure-loss decomposition certified; no result fields corrected.'}
            rows.append(row)
            if record['ifc_id']==475279:
                examples.append(row)
        reports.append({'model_id':data['model_id'],'status_counts':dict(reasons),
            'effective_length_ratio_summary':{'n':len(ratios),'median':statistics.median(ratios),
                'minimum':min(ratios),'maximum':max(ratios),
                'quartiles_inclusive':statistics.quantiles(ratios,n=4,method='inclusive') if len(ratios)>=4 else None,
                'abs_relative_difference_over_1pct':sum(abs(r-1)>.01 for r in ratios),
                'abs_relative_difference_over_10pct':sum(abs(r-1)>.1 for r in ratios),
                'ratio_within_5pct_of_two':sum(abs(r-2)<=.1 for r in ratios)} if ratios else None,
            'Pituus_mm_candidate_vs_axis':{'n':len(property_errors),'median_relative_error':statistics.median(property_errors),
                'relative_error_over_1pct':sum(r>.01 for r in property_errors)} if property_errors else None,
            'source_examples':examples})
    with (folder/'pipe-length-loss-review.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    result={'artifact_type':'source_pipe_length_definition_diagnostic','status':'REQUIRES_ENGINEERING_REVIEW',
        'inputHashes':hashes,'codeSha256':sha(Path(__file__)),'models':reports,
        'screening_scope':'1%/10% and ratio-two bands are descriptive diagnostics, not acceptance criteria or optimization scenarios.',
        'limitations':['Painehäviö may include losses not represented by the per-metre field.',
            'Rounding, design version, effective-length and geometric-length definitions are alternative explanations.',
            'No source engineering value overwritten and no pressure model calibrated from this screen.']}
    (folder/'pipe-length-loss-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps(result,ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
