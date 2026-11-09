"""Recompute sensitivity accounting from stored arm records. Does not rerun physics or edit results."""
import hashlib
import json
from collections import Counter
from pathlib import Path

P = Path(__file__).resolve().parents[1]
ROOT = P / 'experiments/results/source-network-sensitivity-20261007-v1'
SUMMARY = ROOT / 'sensitivity-summary.json'
BASELINE = P / 'experiments/results/source-network-dsh-20261006/source-network-results.json'
EXPECTED_BASELINE = 'b626d640c9bed9cd45a51a77262e57097abf2906d79d90d756f6ab6cb3f73c01'
OUT = ROOT / 'independent-audit'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(checks, name, ok, evidence):
    checks.append({'name': name, 'status': 'PASS' if ok else 'FAIL', 'evidence': evidence})


def arm_files():
    return sorted(p for p in ROOT.glob('*-*.json') if p.name.count('-') and p.stem.rsplit('-', 1)[-1] in ('fixed', 'regenerated'))


def recompute(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    records = data['records']
    reasons = Counter(row['reason'] for row in records)
    bad_objective = sum((row['model_feasible'] and row.get('objective') is None) or (not row['model_feasible'] and row.get('objective') is not None) for row in records)
    frozen = data['policies']['frozen_label_assessment']['minimax_regret']
    selected = frozen['selected']
    held = [row for row in records if row['candidate_id'] == selected and row['split'] == 'held_out']
    failures = sum(not row['model_feasible'] for row in held)
    hypothetical = data['policies']['selections']['minimax_regret'].get('selected')
    return {
        'variant_id': data['variant_id'], 'arm': data['arm'], 'n': len(records),
        'reasons': dict(reasons), 'bad_objective': bad_objective, 'held_n': len(held),
        'failure_count': failures, 'stored_failure_count': frozen.get('failure_count'),
        'changed': hypothetical != selected, 'stored_changed': frozen.get('selection_changed'),
        'hypothetical': hypothetical, 'selected': selected,
    }


def main():
    checks = []
    summary_hash = sha(SUMMARY)
    summary = json.loads(SUMMARY.read_text(encoding='utf-8'))
    check(checks, 'baseline-hash', sha(BASELINE) == EXPECTED_BASELINE == summary['baseline_sha256'], sha(BASELINE))
    rows = [recompute(path) for path in arm_files()]
    check(checks, 'arm-file-count', len(rows) == 165, len(rows))
    check(checks, 'record-width', all(row['n'] == 405 and row['held_n'] == 12 for row in rows), Counter(row['n'] for row in rows))
    check(checks, 'null-objectives-preserved', all(row['bad_objective'] == 0 for row in rows), sum(row['bad_objective'] for row in rows))
    check(checks, 'stored-failure-fields', all(row['failure_count'] == row['stored_failure_count'] for row in rows), 'recomputed from held-out records')
    check(checks, 'stored-change-fields', all(row['changed'] == row['stored_changed'] for row in rows), 'hypothetical selection versus frozen label')
    expected = summary['summary']
    for arm in ('fixed', 'regenerated'):
        subset = [row for row in rows if row['arm'] == arm and row['variant_id'] != 'nominal']
        labels = Counter(row['hypothetical'] for row in subset)
        changed = sum(row['changed'] for row in subset)
        failed = sum(row['failure_count'] > 0 for row in subset)
        target = expected[arm]
        check(checks, arm + '-count-label-failure', len(subset) == target['variants'] and changed == target['changed_regret_selection'] and failed == target['frozen_label_failed_or_unknown'] and dict(labels) == target['selection_counts'], {'n': len(subset), 'changed': changed, 'failed_labels': failed, 'labels': labels})
    nominal = next(row for row in rows if row['variant_id'] == 'nominal' and row['arm'] == 'fixed')
    check(checks, 'nominal-reference-statuses', nominal['reasons'] == {'PASS_CONDITIONAL_RADIAL_MODEL_ONLY': 128, 'VELOCITY_SCREEN_FAILURE': 241, 'UNRESOLVED_TRANSITIONAL_FLOW': 36}, nominal['reasons'])
    groups = {
        'data-validation.json': ['baseline-hash', 'arm-file-count', 'record-width', 'null-objectives-preserved', 'nominal-reference-statuses'],
        'statistical-audit.json': ['stored-failure-fields', 'nominal-reference-statuses'],
        'reproduction-check.json': ['stored-change-fields', 'fixed-count-label-failure', 'regenerated-count-label-failure'],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    statuses = {}
    for name, wanted in groups.items():
        chosen = [item for item in checks if item['name'] in wanted]
        status = 'PASS' if chosen and all(item['status'] == 'PASS' for item in chosen) else 'FAIL'
        statuses[name] = status
        report = {
            'status': status,
            'scope': 'STORED_ARM_RECORD_AUDIT_NOT_PHYSICS_REEXECUTION_OR_FIELD_APPROVAL',
            'resultSha256': summary_hash,
            'baselineSha256': EXPECTED_BASELINE,
            'command': 'python -X utf8 code/audit_sensitivity_records.py',
            'sourceHashes': {str(SUMMARY.relative_to(P)): summary_hash, str(BASELINE.relative_to(P)): sha(BASELINE), str(Path(__file__).relative_to(P)): sha(Path(__file__))},
            'checks': chosen,
            'limitations': ['Does not rerun Darcy/Colebrook or candidate generation from IFC inputs.', 'Illustrative parameter ranges remain assumptions.', 'No inferential intervals are claimed.'],
        }
        (OUT / name).write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'statuses': statuses, 'checks': [(c['name'], c['status']) for c in checks], 'resultSha256': summary_hash}))
    if any(status != 'PASS' for status in statuses.values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
