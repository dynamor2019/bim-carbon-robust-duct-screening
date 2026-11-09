"""Add bounded evidence without modifying the authoritative source experiment."""

import argparse
import copy
import csv
import hashlib
import json
import math
from collections import Counter
from functools import lru_cache
from pathlib import Path

import networkx as nx
import scipy

import source_network_model as network_model
from finite_candidate_decisions import Evaluation, held_out_evaluate
from run_source_network_experiment import choose_policies, generate_candidates, inputs, scenario_set
from source_sensitivity_benchmarks import benchmark
from source_sensitivity_protocol import MISSING_IDS, make_protocol

BASELINE_HASH = 'b626d640c9bed9cd45a51a77262e57097abf2906d79d90d756f6ab6cb3f73c01'
FIELDS = ('candidate_id', 'scenario_id', 'split', 'model_feasible', 'reason', 'objective',
          'required_pressure_Pa', 'ideal_controlled_fan_annual_kWh', 'duct_shell_mass_kg',
          'duct_A1_A3_B4_kgco2e', 'ideal_fan_B6_kgco2e')


def digest(path):
    """Hash immutable source and executable identities."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    """Write only newly created analysis outputs; reject nonfinite JSON."""
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def install_pressure_cache():
    """Memoize the unchanged pure loss function only inside this analysis process."""
    original = network_model.pressure_loss
    @lru_cache(maxsize=150000)
    def cached(flow, length, diameter, density, viscosity, roughness):
        """Cache by every physics input, not by a candidate label."""
        return original(flow, length, diameter, dict(density_kg_m3=density,
                        kinematic_viscosity_m2_s=viscosity, roughness_m=roughness))
    def wrapper(flow, length, diameter, parameters):
        """Keep the existing physics signature and result unchanged."""
        return cached(flow, length, diameter, parameters['density_kg_m3'],
                      parameters['kinematic_viscosity_m2_s'], parameters['roughness_m'])
    network_model.pressure_loss = wrapper
    return original


def variant_inputs(register, dimensions, factors):
    """Replace only disclosed parameters; never alter known source dimensions."""
    updated_register, updated_dimensions = copy.deepcopy(register), copy.deepcopy(dimensions)
    for name, value in factors.items():
        if name.startswith('dimension_'):
            identifier = int(name.split('_')[1])
            if updated_dimensions[identifier]['origin'] != 'ASSUMED_MISSING_COMPONENT_DIMENSION':
                raise ValueError('Refusing substitution of a known source section')
            updated_dimensions[identifier].update(diameter=value, area=math.pi * value ** 2 / 4,
                                                  perimeter=math.pi * value)
        elif name == 'local_loss_multiplier':
            updated_register['parameters']['missing_local_loss_coefficients'] = {
                key: coefficient * value for key, coefficient in
                register['parameters']['missing_local_loss_coefficients'].items()}
        else:
            updated_register['parameters'][name] = value
    return updated_register, updated_dimensions


def fixed_candidates(candidates, dimensions):
    """Freeze design interventions; update only unresolved source-sized components."""
    result = {}
    for identifier, candidate in candidates.items():
        sizes = {node: dict(size) for node, size in candidate['sizes'].items()}
        for node in set(sizes).intersection(MISSING_IDS):
            if sizes[node]['origin'] == 'ASSUMED_MISSING_COMPONENT_DIMENSION':
                sizes[node] = dict(dimensions[node])
        result[identifier] = dict(candidate, sizes=sizes)
    return result


def evaluate(candidates, components, terminals, register):
    """Save every cell, distinguishing unresolved states from definite failures."""
    records, matrices = [], {}
    for identifier, candidate in candidates.items():
        matrices[identifier] = {}
        for scenario in scenario_set(register):
            demands = {node: load * scenario['demand'] for node, load in terminals.items()}
            parameters = dict(register['parameters'], grid_kgco2e_kwh=scenario['grid'])
            outcome = network_model.evaluate_tree(candidate['tree'], candidate['sizes'],
                                                  components, demands, parameters)
            matrices[identifier][scenario['id']] = Evaluation(outcome['model_feasible'], outcome['objective'])
            row = dict(outcome, candidate_id=identifier, scenario_id=scenario['id'], split=scenario['split'])
            records.append({name: row.get(name) for name in FIELDS})
    return records, matrices


def policy_evidence(matrices, register, baseline_policies):
    """Separate previously frozen choices from hypothetical design-only reselection."""
    held_ids = [scenario['id'] for scenario in scenario_set(register) if scenario['split'] == 'held_out']
    design_ids = [scenario['id'] for scenario in scenario_set(register) if scenario['split'] == 'design']
    held = {key: {sid: rows[sid] for sid in held_ids} for key, rows in matrices.items()}
    selections = choose_policies(matrices, register)
    comparisons = {}
    for mode, baseline in baseline_policies.items():
        identifier = baseline['selected']
        if identifier not in matrices:
            comparisons[mode] = dict(selected=identifier, status='MISSING_CANDIDATE_NOT_IMPUTED')
            continue
        performance = held_out_evaluate(held, held_ids, design_ids, identifier)
        comparisons[mode] = dict(performance,
            design_feasible_count=sum(matrices[identifier][sid].feasible for sid in design_ids),
            hypothetical_reselection=selections[mode].get('selected'),
            selection_changed=selections[mode].get('selected') != identifier)
    return dict(selections=selections, frozen_label_assessment=comparisons)


def verify_baseline(records, baseline):
    """Require exact nominal cell accounting before any new perturbation run."""
    if len(records) != len(baseline['records']):
        raise ValueError('Baseline record count mismatch')
    old = {(row['candidate_id'], row['scenario_id']): row for row in baseline['records']}
    for row in records:
        if not set(FIELDS).issubset(row):
            raise ValueError('Incomplete baseline record')
        expected = old[(row['candidate_id'], row['scenario_id'])]
        for name in FIELDS:
            actual, reference = row[name], expected.get(name)
            if isinstance(actual, (int, float)) and not isinstance(actual, bool):
                equal = isinstance(reference, (int, float)) and not isinstance(reference, bool) and math.isclose(
                    actual, reference, rel_tol=1e-12, abs_tol=1e-10)
            else:
                equal = actual == reference
            if not equal:
                raise ValueError(f'Baseline mismatch: {row["candidate_id"]}/{row["scenario_id"]}/{name}')


def table_rows(baseline):
    """Expand all twelve held-out results with full feasible-cell oracle and counts."""
    selected = baseline['selections']['minimax_regret']['selected']
    scenarios = sorted({r['scenario_id'] for r in baseline['records'] if r['split'] == 'held_out'})
    rows = []
    for scenario in scenarios:
        cells = [row for row in baseline['records'] if row['scenario_id'] == scenario]
        chosen = next(row for row in cells if row['candidate_id'] == selected)
        feasible = [row['objective'] for row in cells if row['model_feasible']]
        optimum = min(feasible) if feasible else None
        rows.append(dict(scenario_id=scenario, demand_multiplier=chosen['demand_multiplier'],
            grid_kgco2e_kwh=chosen['grid_kgco2e_kwh'], selected_objective=chosen['objective'],
            recorded_feasible_optimum=optimum,
            conditional_regret=chosen['objective'] - optimum if chosen['model_feasible'] else None,
            feasible_count=len(feasible), unknown_count=sum(r['reason'] == 'UNRESOLVED_TRANSITIONAL_FLOW' for r in cells)))
    return rows


def summarize(studies):
    """Use descriptive counts, never call sampling frequencies probabilities."""
    summary = {}
    for arm in ('fixed', 'regenerated'):
        selected = [study for study in studies if study['arm'] == arm and study['variant_id'] != 'nominal']
        summary[arm] = dict(variants=len(selected),
            selection_counts=dict(Counter(s['policies']['selections']['minimax_regret'].get('selected') for s in selected)),
            changed_regret_selection=sum(s['policies']['frozen_label_assessment']['minimax_regret'].get('selection_changed', True) for s in selected),
            frozen_label_failed_or_unknown=sum(s['policies']['frozen_label_assessment']['minimax_regret'].get('failure_count', 12) > 0 for s in selected),
            status_totals=dict(sum((Counter(s['statuses']) for s in selected), Counter())))
    return summary


def execute_variants(context, destination, protocol):
    """Execute both fixed and redesigned arms, keeping their meanings separate."""
    source, register, components, terminals, root, contacts, dimensions, candidates, baseline = context
    studies = []
    for variant in protocol['variants']:
        new_register, new_dimensions = variant_inputs(register, dimensions, variant['factors'])
        arms = {'fixed': fixed_candidates(candidates, new_dimensions)}
        disconnected = []
        changed = any(new_dimensions[node]['diameter'] != dimensions[node]['diameter'] for node in MISSING_IDS)
        if changed:
            arms['regenerated'], disconnected = generate_candidates(source, new_register, components, terminals, root, contacts, new_dimensions)
        for arm, family in arms.items():
            records, matrices = evaluate(family, components, terminals, new_register)
            geometry = {key: {'edges': sorted(value['tree'].edges()), 'sizes': value['sizes']} for key, value in family.items()}
            record = dict(variant_id=variant['id'], kind=variant['kind'], arm=arm,
                          statuses=dict(Counter(row['reason'] for row in records)), records=records,
                          disconnected=disconnected if arm == 'regenerated' else [], candidate_designs=geometry,
                          policies=policy_evidence(matrices, new_register, baseline['selections']))
            dump(destination / f"{variant['id']}-{arm}.json", record)
            studies.append({key: value for key, value in record.items() if key not in ('records', 'candidate_designs')})
        print(f"Completed {variant['id']} ({len(arms)} arms)", flush=True)
    return studies


def run(project, destination):
    """Run the registered variants under existing physics, not an external writer."""
    baseline_path = project / 'experiments/results/source-network-dsh-20261006/source-network-results.json'
    if destination.exists() or digest(baseline_path) != BASELINE_HASH:
        raise ValueError('New destination and unchanged baseline required')
    baseline = json.loads(baseline_path.read_text(encoding='utf-8'))
    source, register, components, terminals, root, contacts, hashes = inputs(project)
    dimensions, assumptions = network_model.prepare_dimensions(components)
    if set(a['ifc_id'] for a in assumptions if a['parameter'] == 'hydraulic_section') != set(MISSING_IDS):
        raise ValueError('Unexpected missing-dimension set')
    candidates, disconnected = generate_candidates(source, register, components, terminals, root, contacts, dimensions)
    executable_names = ('source_sensitivity.py', 'source_sensitivity_protocol.py', 'source_sensitivity_benchmarks.py',
                        'source_network_model.py', 'source_anchored_physics.py', 'run_source_network_experiment.py',
                        'finite_candidate_decisions.py')
    code_hashes = {name: digest(project / 'code' / name) for name in executable_names}
    destination.mkdir(parents=True)
    protocol = make_protocol()
    dump(destination / 'protocol.json', protocol)
    dump(destination / 'equation-benchmark.json', benchmark(register['parameters'], candidates, terminals))
    nominal, matrices = evaluate(candidates, components, terminals, register)
    verify_baseline(nominal, baseline)
    dump(destination / 'baseline-held-out.json', table_rows(baseline))
    original = install_pressure_cache()
    try:
        context = source, register, components, terminals, root, contacts, dimensions, candidates, baseline
        studies = execute_variants(context, destination, protocol)
    finally:
        network_model.pressure_loss = original
    if digest(baseline_path) != BASELINE_HASH or any(digest(project / 'code' / name) != value for name, value in code_hashes.items()):
        raise ValueError('Immutable result or executable changed during analysis')
    dump(destination / 'sensitivity-summary.json', dict(status='COMPUTED_NOT_SCIENTIFIC_APPROVAL',
        baseline_sha256=BASELINE_HASH, source_hashes=hashes, code_hashes=code_hashes,
        software={'networkx': nx.__version__, 'scipy': scipy.__version__},
        field_validation=False, studies=studies, summary=summarize(studies)))
    with (destination / 'baseline-held-out.csv').open('w', encoding='utf-8', newline='') as stream:
        rows = table_rows(baseline)
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(summarize(studies)), flush=True)


def main():
    """Require a new destination and keep the original calculation untouched."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    run(Path(__file__).resolve().parents[1], args.output_dir.resolve())


if __name__ == '__main__':
    main()
