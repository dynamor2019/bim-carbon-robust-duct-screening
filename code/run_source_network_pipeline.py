"""DSH-owned replay entry: execute model, independently audit, and publish scoped evidence."""

import csv
import json
from collections import Counter
from pathlib import Path

from audit_source_network_experiment import audit, sha
from run_source_network_experiment import run


def publish_evidence(project, result_path):
    """Emit real computed gate evidence, never author or field-approval declarations."""
    destination = result_path.parent / 'independent-audit'
    numerical = json.loads((destination / 'numerical-audit.json').read_text(encoding='utf-8'))
    result = json.loads(result_path.read_text(encoding='utf-8'))
    statistical = dict(numerical)
    statistical['scope'] = 'DETERMINISTIC_SCENARIO_ACCOUNTING_NO_INFERENTIAL_STATISTICS'
    expected = len(result['candidate_designs']) * 15
    unique = {(row['candidate_id'], row['scenario_id']) for row in result['records']}
    checks = [('complete-factorial-accounting', len(unique) == len(result['records']) == expected,
               f'{len(result["candidate_designs"])} alternatives x 15 deterministic cases; {len(unique)} unique records.'),
              ('nonfinite-adverse-outcomes-retained', all(row['objective'] is None for row in result['records'] if not row['model_feasible']),
               'All failed and unresolved objectives remain null; no zero backfilling.'),
              ('no-field-claims', result['field_validation'] is False, 'Numerical model verification only, not field approval.')]
    statistical['checks'] = [{'name': name, 'status': 'PASS' if passed else 'FAIL', 'evidence': evidence}
                             for name, passed, evidence in checks]
    statistical['status'] = 'PASS' if all(passed for _, passed, _ in checks) else 'FAIL'
    statistical['counts'] = dict(Counter(row['reason'] for row in result['records']))
    if statistical['status'] != 'PASS':
        raise ValueError('Scenario accounting failed; do not advance to writing')
    target = destination
    for name, data in [('reproduction-check.json', numerical), ('statistical-audit.json', statistical)]:
        (target / name).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    with (target / 'result-provenance.tsv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream, delimiter='\t')
        writer.writerow(['claim_id', 'evidence', 'result_sha256', 'scope', 'status'])
        for row in result['records']:
            writer.writerow([row['candidate_id'] + '/' + row['scenario_id'], str(result_path), sha(result_path),
                             'CONDITIONAL_MODEL_CALCULATION_NOT_MEASUREMENT:' + row['reason'], 'VERIFIED'])


def main():
    """Fixed project-relative replay destination; no caller-supplied shell or synthetic fallback."""
    project = Path(__file__).resolve().parents[1]
    destination = project / 'experiments/results/source-network-dsh-20261006'
    result_path = destination / 'source-network-results.json'
    run(project, destination)
    audit(project, result_path)
    publish_evidence(project, result_path)


if __name__ == '__main__':
    main()
