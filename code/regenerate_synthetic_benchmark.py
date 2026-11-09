"""Replay the same registered experiment after interface repairs and record an honest run receipt.
Not a CLI paper pipeline and never edits pipeline checkpoint/provider settings.
"""
from datetime import datetime,timezone
import hashlib
from pathlib import Path
import subprocess
import sys


def main():
    p=Path(__file__).resolve().parent.parent
    command=[sys.executable,'-X','utf8',str(p/'code/run_synthetic_route_size.py'),'--results-file',str(p/'experiments/results/synthetic-route-size-results.json')]
    log=p/'milestones/reproducibility/logs/experiment-run.log'
    archive=p/'.dsh-state/experiment-failures';archive.mkdir(parents=True,exist_ok=True)
    if log.exists():
        old=log.read_bytes();(archive/('experiment-run-'+hashlib.sha256(old).hexdigest()+'.log')).write_bytes(old)
    result_file=p/'experiments/results/synthetic-route-size-results.json'
    if result_file.exists():
        old=result_file.read_bytes();(archive/('synthetic-result-'+hashlib.sha256(old).hexdigest()+'.json')).write_bytes(old)
    started=datetime.now(timezone.utc).isoformat()
    result=subprocess.run(command,cwd=p,capture_output=True,text=True,encoding='utf-8')
    finished=datetime.now(timezone.utc).isoformat()
    digest=hashlib.sha256(result_file.read_bytes()).hexdigest() if result.returncode==0 else 'UNAVAILABLE_FAILED_RUN'
    log.parent.mkdir(parents=True,exist_ok=True)
    log.write_text('started='+started+'\nfinished='+finished+'\nstatus='+('SUCCESS' if result.returncode==0 else 'FAILED')+'\ncommand='+subprocess.list2cmdline(command)+'\nresults_file='+str(result_file)+'\nresult_sha256='+digest+'\nreceipt_origin=PROJECT_DETERMINISTIC_REEXECUTION_AFTER_INTERFACE_REPAIR_NOT_PIPELINE_REPLAY\n\n'+result.stdout+'\n'+result.stderr,encoding='utf-8')
    print(result.stdout,end='');print(result.stderr,end='',file=sys.stderr)
    raise SystemExit(result.returncode)


if __name__=='__main__':main()
