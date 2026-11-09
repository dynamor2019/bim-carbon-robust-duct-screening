"""Reexecute the frozen numerical benchmark outside the source project."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


RESULT = 'experiments/results/synthetic-route-size-results.json'
BASE = 'milestones/reproducibility'
SCRIPTS = (
    'code/finite_candidate_decisions.py',
    'code/run_synthetic_route_size.py',
    'code/regenerate_synthetic_benchmark.py',
    'code/validate_synthetic_benchmark.py',
    'code/summarize_synthetic_benchmark.py',
    'code/prepare_manuscript_evidence.py',
    BASE + '/extend_input_provenance.py',
    BASE + '/assemble_display_fragments.py',
)
INPUTS = (
    RESULT,
    'milestones/synthetic-benchmark-protocol.md',
    BASE + '/local-spatial-domain-freeze.json',
    BASE + '/synthetic-data/synthetic-data-register.json',
    BASE + '/synthetic-data/synthetic-input-sanity.json',
)


def file_hash(path):
    """Return the exact bytes' SHA256 digest."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contained_file(root, relative):
    """Reject absent inputs and links escaping the source project."""
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('Missing or out-of-project input: ' + relative)
    return path


def comparison(reference, replayed):
    """Ignore only runtime metadata, retaining all scientific fields."""
    keys = set(reference) | set(replayed)
    differences = [key for key in sorted(keys - {'environment'})
                   if key not in reference or key not in replayed
                   or reference[key] != replayed[key]]
    return differences


def create_workspace(source, destination):
    """Create a new workspace; never accept an existing or overlapping path."""
    source = source.resolve()
    if destination is None:
        destination = Path(tempfile.mkdtemp(prefix='paper-numerical-replay-')).resolve()
        if destination.is_relative_to(source) or source.is_relative_to(destination):
            raise ValueError('Temporary output overlaps the source project')
    else:
        destination = destination.resolve()
        if (destination.is_relative_to(source)
                or source.is_relative_to(destination) or destination.exists()):
            raise ValueError('Output must be a new directory outside the project')
        destination.mkdir(parents=True)
    return destination


def stage_files(source, destination):
    """Copy only the numerical scripts and registered inputs, byte for byte."""
    files = SCRIPTS + INPUTS
    paths = {name: contained_file(source, name) for name in files}
    snapshots = {name: file_hash(path) for name, path in paths.items()}
    for name, path in paths.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    (destination / '.dsh-state/writing').mkdir(parents=True)
    return snapshots


def execute(workspace, script, extra=()):
    """Run a known project script and retain its complete failure log."""
    process = subprocess.run(
        [sys.executable, '-X', 'utf8', str((workspace / script).resolve()), *extra],
        cwd=workspace,
        capture_output=True, text=True, encoding='utf-8', timeout=120,
    )
    logs = workspace / 'isolated-logs'
    logs.mkdir(exist_ok=True)
    log_path = logs / (Path(script).stem + '.log')
    log_path.write_text(process.stdout + '\n' + process.stderr, encoding='utf-8')
    if process.returncode:
        raise RuntimeError(f'{script} failed; inspect {log_path}')


def verify_displays(workspace):
    """Check every claim's source binding, both ledgers and all table rows."""
    ledger = workspace / BASE / 'result-provenance.tsv'
    with ledger.open(encoding='utf-8', newline='') as stream:
        claims = list(csv.DictReader(stream, delimiter='\t'))
    if len(claims) != 159 or len({row['claim_id'] for row in claims}) != 159:
        raise ValueError('Expected 159 unique claims after all display steps')
    for row in claims:
        source = contained_file(workspace, row['source_file'].replace('\\', '/'))
        if row['status'] != 'VERIFIED' or file_hash(source) != row['source_sha256']:
            raise ValueError('Stale or unverified claim: ' + row['claim_id'])
    if ledger.read_bytes() != (workspace / 'milestones/result-provenance.tsv').read_bytes():
        raise ValueError('Workflow and numerical ledgers disagree')
    table = workspace / BASE / 'tables/synthetic-method-comparison.tsv'
    with table.open(encoding='utf-8', newline='') as stream:
        if len(list(csv.DictReader(stream, delimiter='\t'))) != 96:
            raise ValueError('Expected all 96 policy/setting rows')


def reproduce(source, destination=None):
    """Retain rerun bytes, compare science, then derive reference-bound displays."""
    source = source.resolve()
    for name in SCRIPTS + INPUTS:
        contained_file(source, name)
    workspace = create_workspace(source, destination)
    snapshots = stage_files(source, workspace)
    receipt = {'status': 'FAILED', 'workspace': str(workspace),
               'scope': 'LOCAL_ISOLATED_NUMERICAL_REEXECUTION_NOT_EXTERNAL_REPLICATION',
               'figures': 'NOT_INCLUDED_IN_NUMERICAL_REPLAY_SCOPE'}
    try:
        execute(workspace, 'code/run_synthetic_route_size.py', ('--validate-only',))
        execute(workspace, 'code/regenerate_synthetic_benchmark.py')
        replay = workspace / RESULT
        reference = source / RESULT
        receipt['reference_sha256'] = file_hash(reference)
        receipt['reexecuted_sha256'] = file_hash(replay)
        fresh_result = workspace / 'reexecuted-result.json'
        shutil.copyfile(replay, fresh_result)
        differences = comparison(json.loads(reference.read_text(encoding='utf-8')),
                                 json.loads(replay.read_text(encoding='utf-8')))
        receipt['scientific_field_differences'] = differences
        if differences:
            raise ValueError('Reexecution differs scientifically: ' + str(differences))
        execute(workspace, 'code/validate_synthetic_benchmark.py')
        # Keep the rerun and gates separate from original-hash-bound displays.
        shutil.copytree(workspace / BASE / 'synthetic-data',
                        workspace / 'reexecuted-gates')
        shutil.copyfile(reference, replay)
        for script in ('code/validate_synthetic_benchmark.py',
                       'code/summarize_synthetic_benchmark.py',
                       'code/prepare_manuscript_evidence.py',
                       BASE + '/extend_input_provenance.py',
                       BASE + '/assemble_display_fragments.py'):
            execute(workspace, script)
        verify_displays(workspace)
        receipt['status'] = 'PASS_NUMERICAL_REEXECUTION_AND_REFERENCE_BOUND_DISPLAYS'
        receipt['numeric_claims'] = 159
        receipt['policy_setting_rows'] = 96
    finally:
        unchanged = all(file_hash(source / name) == digest
                        for name, digest in snapshots.items())
        receipt['source_files_unchanged'] = unchanged
        if not unchanged:
            receipt['status'] = 'FAILED_SOURCE_CHANGED'
        (workspace / 'isolated-reproduction.json').write_text(
            json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    if not unchanged:
        raise ValueError('Source files changed during reproduction')
    return receipt


def main():
    """Parse the optional new output directory and run without installing packages."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path)
    args = parser.parse_args()
    try:
        receipt = reproduce(Path(__file__).resolve().parent.parent, args.output_root)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        parser.exit(1, str(error) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
