"""Run finite route-tree/section comparisons under registered source-project assumptions."""

import argparse
import hashlib
import json
from pathlib import Path

import networkx as nx

from finite_candidate_decisions import Evaluation, NoFeasibleDesign, select
from source_network_model import build_graph, build_tree, designs, evaluate_tree, prepare_dimensions


def sha(path):
    """Return exact input/executable identity."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs(project):
    """Keep source data and assumed parameters separate, checking existing typed units."""
    base = project / 'milestones/reproducibility'
    source_path = base / 'network-interfaces/concrete-interfaces.json'
    register_path = base / 'model-assumptions/network-experiment.json'
    source = json.loads(source_path.read_text(encoding='utf-8'))
    register = json.loads(register_path.read_text(encoding='utf-8'))
    unit_path = source_path.with_name('native-property-unit-review.json')
    units = json.loads(unit_path.read_text(encoding='utf-8'))
    if register['source_sha256'] != sha(source_path) or units['inputHashes'][source_path.name] != sha(source_path):
        raise ValueError('Stale source or typed-unit evidence')
    if units['status'] != 'PASS_TYPED_UNIT_RESOLUTION' or source['length_unit_scale_to_m'] != 0.001:
        raise ValueError('Failed or incompatible source units')
    components = {c['ifc_id']: c for c in source['components'] if c['ifc_type'] != 'IfcFan'}
    terminals = {}
    for identifier, component in components.items():
        if component['ifc_type'] != 'IfcAirTerminal':
            continue
        value = component['psets'].get('FI_Tekninen', {}).get('Virtaama')
        if type(value) not in (int, float) or value <= 0:
            raise ValueError('Missing positive terminal source demand; register it before running')
        terminals[identifier] = value * 0.001
    ducts = [c for c in components.values() if c['ifc_type'] == 'IfcDuctSegment']
    root = min(ducts, key=lambda c: (-c['psets'].get('FI_Tekninen', {}).get('Virtaama', 0), c['ifc_id']))['ifc_id']
    contacts = project.parent / 'research_data/pilot_inferred_contacts.csv'
    return source, register, components, terminals, root, contacts, {
        'source': sha(source_path), 'register': sha(register_path), 'units': sha(unit_path), 'contacts': sha(contacts)}


def scenario_set(register):
    """Disjoint named design/assessment sets are deterministic stress scenarios, not samples."""
    design = [{'id': 'D' + str(i), 'demand': value, 'grid': register['parameters']['grid_kgco2e_kwh'], 'split': 'design'}
              for i, value in enumerate(register['design_demand_multipliers'])]
    held = [{'id': 'H' + str(i) + '_' + str(j), 'demand': value, 'grid': grid, 'split': 'held_out'}
            for i, value in enumerate(register['held_out_demand_multipliers'])
            for j, grid in enumerate(register['held_out_grid_factors'])]
    return design + held


def generate_candidates(source, register, components, terminals, root, contacts, dimensions):
    """Freeze finite graph/sizing alternatives before evaluating their outcomes."""
    candidates, failures = {}, []
    for tolerance in register['contact_tolerances_m']:
        graph = build_graph(components, contacts, source['model_id'], tolerance, dimensions)
        for route_mode in register['route_modes']:
            tree, missing = build_tree(graph, root, route_mode, terminals)
            if tree is None:
                failures.append({'tolerance_m': tolerance, 'route_mode': route_mode, 'missing_terminals': missing})
                continue
            for size_mode in register['sizing_modes']:
                identifier = f't{tolerance:g}_{route_mode}_{size_mode}'
                sizes = designs(tree, terminals, dimensions, register['parameters'], size_mode)
                candidates[identifier] = {'tree': tree, 'sizes': sizes, 'tolerance': tolerance,
                                          'route_mode': route_mode, 'size_mode': size_mode}
    return candidates, failures


def evaluations(candidates, components, terminals, register):
    """Calculate outcomes instead of generating or backfilling favorable results."""
    rows, matrices = [], {}
    for identifier, candidate in candidates.items():
        matrix = {}
        for scenario in scenario_set(register):
            parameters = dict(register['parameters'], grid_kgco2e_kwh=scenario['grid'])
            demands = {key: value * scenario['demand'] for key, value in terminals.items()}
            result = evaluate_tree(candidate['tree'], candidate['sizes'], components, demands, parameters)
            matrix[scenario['id']] = Evaluation(result['model_feasible'], result['objective'])
            rows.append(dict(result, candidate_id=identifier, scenario_id=scenario['id'], split=scenario['split'],
                             demand_multiplier=scenario['demand'], grid_kgco2e_kwh=scenario['grid'],
                             data_origin='SOURCE_ANCHORED_MODELLED_EXPERIMENT'))
        matrices[identifier] = matrix
    return rows, matrices


def choose_policies(matrices, register):
    """Use the existing tested exact-selection engine, keeping infeasible selections undefined."""
    scenario_ids = ['D' + str(i) for i in range(len(register['design_demand_multipliers']))]
    nominal = 'D' + str(register['design_demand_multipliers'].index(1.0))
    selections = {}
    for mode in ('deterministic', 'minimax', 'minimax_regret'):
        try:
            selections[mode] = select({key: {sid: rows[sid] for sid in scenario_ids}
                                       for key, rows in matrices.items()}, scenario_ids, mode, nominal)
        except NoFeasibleDesign as error:
            selections[mode] = {'selected': None, 'status': 'NO_FEASIBLE_MODEL_DESIGN', 'reason': str(error)}
    return selections


def run(project, destination):
    """Save a new immutable experiment, without touching the old paper or claiming field certification."""
    if destination.exists():
        raise ValueError('New destination required; no existing result overwrite')
    source, register, components, terminals, root, contacts, hashes = inputs(project)
    dimensions, assumptions = prepare_dimensions(components)
    candidates, failures = generate_candidates(source, register, components, terminals, root, contacts, dimensions)
    if not candidates:
        raise ValueError('No source-graph candidate connects every required terminal; do not invent connectivity')
    rows, matrices = evaluations(candidates, components, terminals, register)
    result = {'artifact_type': 'conditional_source_project_finite_network_experiment',
              'data_origin': 'SOURCE_ANCHORED_MODELLED_EXPERIMENT', 'sourceHashes': hashes,
              'model_id': source['model_id'], 'system_name': source['system_name'],
              'source_roles': register['source_roles'], 'assumed_pressure_root_ifc_id': root,
              'terminal_count': len(terminals), 'source_terminal_total_m3_s': sum(terminals.values()),
              'model_assumptions': register, 'generated_component_parameters': assumptions,
              'disconnected_candidates': failures, 'records': rows,
              'selections': choose_policies(matrices, register),
              'candidate_designs': {key: {'edges': sorted(candidate['tree'].edges()), 'sizes': candidate['sizes']}
                                    for key, candidate in candidates.items()},
              'software': {'networkx': nx.__version__}, 'field_validation': False,
              'codeHashes': {name: sha(Path(__file__).with_name(name)) for name in
                             ('run_source_network_experiment.py', 'source_network_model.py',
                              'source_anchored_physics.py', 'finite_candidate_decisions.py')}}
    destination.mkdir(parents=True)
    path = destination / 'source-network-results.json'
    path.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'path': str(path), 'sha256': sha(path), 'candidates': len(candidates),
                      'records': len(rows), 'terminals': len(terminals), 'selections': result['selections']}))


def main():
    """Explicit path required; no accidental override of the current pipeline dataset."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    run(Path(__file__).resolve().parents[1], args.output_dir)


if __name__ == '__main__':
    main()
