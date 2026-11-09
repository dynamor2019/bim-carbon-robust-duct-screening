"""Append source/result validation outcomes with complete immutable evidence snapshots."""
import argparse
import csv
import json
from datetime import datetime,timezone
from pathlib import Path
from recover_fitting_interfaces import sha


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('report')
    parser.add_argument('--gate',required=True)
    args=parser.parse_args()
    project=Path(__file__).resolve().parents[1]
    report=(project/args.report).resolve()
    if not report.is_relative_to((project/'milestones').resolve()):
        raise ValueError('Validation report must be inside project milestones')
    evidence=json.loads(report.read_text(encoding='utf-8'))
    report_sha=sha(report)
    status=evidence.get('status')
    if not isinstance(status,str):
        raise ValueError('Validation status missing')
    history_path=project/'milestones/reproducibility/validation-history.json'
    history=json.loads(history_path.read_text(encoding='utf-8')) if history_path.exists() else {'artifact_type':'validation_outcome_history','records':[]}
    if any(r['gate']==args.gate and r['report_sha256']==report_sha for r in history['records']):
        print('Outcome already recorded; no duplicate added')
        return
    record={'recorded_at':datetime.now(timezone.utc).isoformat(),'gate':args.gate,'status':status,
        'report_path':str(report.relative_to(project)),'report_sha256':report_sha,'evidence':evidence}
    history['records'].append(record)
    history_path.write_text(json.dumps(history,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    tsv=project/'milestones/data-validation-history.tsv'
    exists=tsv.exists()
    with tsv.open('a',encoding='utf-8',newline='') as stream:
        writer=csv.writer(stream,delimiter='\t',lineterminator='\n')
        if not exists:
            writer.writerow(['recorded_at','gate','status','report_sha256','report_path','retained_evidence'])
        writer.writerow([record['recorded_at'],args.gate,status,report_sha,record['report_path'],str(history_path.relative_to(project))])
    print(json.dumps({k:v for k,v in record.items() if k!='evidence'},indent=2))


if __name__=='__main__':
    main()
