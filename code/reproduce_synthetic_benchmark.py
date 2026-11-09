"""Reproduce registered synthetic artifacts only; never manages the paper pipeline."""
from pathlib import Path
import subprocess
import sys


def main():
    project=Path(__file__).resolve().parent.parent
    commands=[['code/run_synthetic_route_size.py','--validate-only'],
        ['code/regenerate_synthetic_benchmark.py'],['code/validate_synthetic_benchmark.py'],
        ['code/summarize_synthetic_benchmark.py']]
    for args in commands:
        subprocess.run([sys.executable,'-X','utf8',*args],cwd=project,check=True)


if __name__=='__main__':main()
