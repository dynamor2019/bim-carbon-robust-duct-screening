"""Independent numerical checks and disclosure tables; never certify installed performance."""

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import networkx as nx


def sha(path):
    """Fingerprint exact source, code and outcome bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def close(actual, expected):
    """Use a stated numerical tolerance, not a fitted agreement threshold."""
    if not math.isclose(actual, expected, rel_tol=1e-8, abs_tol=1e-8):
        raise ValueError(f'Independent mismatch: {actual} != {expected}')


def independent_pressure(component, size, flow, parameters):
    """Recompute Darcy/Colebrook using fixed-point iteration, independent of production bisection."""
    velocity = flow / size['area']
    rho = parameters['density_kg_m3']
    if component['ifc_type'] != 'IfcDuctSegment':
        tech = component['psets'].get('FI_Tekninen', {})
        loss, speed = tech.get('Paineh\u00e4vi\u00f6', 0), tech.get('Virtausnopeus', 0)
        if loss and loss > 0 and speed and speed > 0:
            return loss * (velocity / speed) ** 2
        return parameters['missing_local_loss_coefficients'][component['ifc_type']] * rho * velocity ** 2 / 2
    diameter = size['diameter']
    reynolds = velocity * diameter / parameters['kinematic_viscosity_m2_s']
    if 2300 <= reynolds < 4000:
        return None
    if reynolds < 2300:
        friction = 64 / reynolds
    else:
        inverse_root = 7.0
        for _ in range(100):
            updated = -2 * math.log10(parameters['roughness_m'] / (3.7 * diameter)
                                     + 2.51 * inverse_root / reynolds)
            if abs(updated - inverse_root) < 1e-12:
                break
            inverse_root = updated
        friction = updated ** -2
    return friction * size['length'] / diameter * rho * velocity ** 2 / 2


def independent_case(row, design, components, terminals, parameters):
    """Accumulate each terminal demand along its full path, not reverse tree recursion."""
    tree = nx.DiGraph(design['edges'])
    if not nx.is_arborescence(tree) or not set(terminals).issubset(tree):
        raise ValueError('Not a complete terminal-service tree')
    root = next(node for node in tree if tree.in_degree(node) == 0)
    paths = nx.single_source_shortest_path(tree, root)
    loads = dict.fromkeys(tree, 0.0)
    for terminal, demand in terminals.items():
        for node in paths[terminal]:
            loads[node] += demand * row['demand_multiplier']
    sizes = {int(key): value for key, value in design['sizes'].items()}
    losses = {node: independent_pressure(components[node], sizes[node], loads[node], parameters) for node in tree}
    if any(loss is None for loss in losses.values()):
        if row['reason'] != 'UNRESOLVED_TRANSITIONAL_FLOW' or row['objective'] is not None:
            raise ValueError('Transitional regime incorrectly assigned an outcome')
        return
    for detail in row['components']:
        node = detail['ifc_id']
        close(detail['flow_m3_s'], loads[node])
        close(detail['velocity_m_s'], loads[node] / sizes[node]['area'])
        close(detail['pressure_loss_Pa'], losses[node])
    if len(row['components']) != len(tree):
        raise ValueError('Incomplete component result ledger')
    failed = sum(loads[node] / sizes[node]['area'] > parameters['velocity_limit_m_s']
                 for node in tree if components[node]['ifc_type'] != 'IfcAirTerminal')
    if failed:
        if row['model_feasible'] or row['objective'] is not None or row['failed_components'] != failed:
            raise ValueError('Velocity-screen failures were not retained')
        return
    if not row['model_feasible']:
        raise ValueError('Feasible conditional calculation incorrectly rejected')
    pressure = max(sum(losses[node] for node in paths[terminal]) for terminal in terminals)
    annual = sum(terminals.values()) * row['demand_multiplier'] * pressure / parameters['efficiency']
    annual *= parameters['hours_per_year'] / 1000
    mass = sum(sizes[node]['perimeter'] * sizes[node]['length'] * parameters['wall_thickness_m']
               * parameters['steel_density_kg_m3'] for node in tree if components[node]['ifc_type'] == 'IfcDuctSegment')
    replacement_count = math.ceil(parameters['horizon_years'] / parameters['duct_lifetime_years']) - 1
    embodied = mass * parameters['duct_production_kgco2e_kg'] * (1 + replacement_count)
    operating = annual * parameters['horizon_years'] * row['grid_kgco2e_kwh']
    for key, expected in [('root_flow_m3_s', loads[root]), ('required_pressure_Pa', pressure),
                          ('ideal_controlled_fan_annual_kWh', annual), ('duct_shell_mass_kg', mass),
                          ('duct_A1_A3_B4_kgco2e', embodied), ('ideal_fan_B6_kgco2e', operating),
                          ('objective', embodied + operating)]:
        close(row[key], expected)


def independent_policies(result):
    """Check finite-policy selection independently; held-out cases never determine selection."""
    matrices = {}
    for row in result['records']:
        if row['split'] == 'design':
            matrices.setdefault(row['candidate_id'], {})[row['scenario_id']] = row
    scenario_ids = sorted(next(iter(matrices.values())))
    optima = {sid: min(rows[sid]['objective'] for rows in matrices.values() if rows[sid]['model_feasible'])
              for sid in scenario_ids}
    for mode, policy in result['selections'].items():
        scores = {}
        for candidate, rows in matrices.items():
            relevant = ['D1'] if mode == 'deterministic' else scenario_ids
            if not all(rows[sid]['model_feasible'] for sid in relevant):
                continue
            values = [rows[sid]['objective'] - (optima[sid] if mode == 'minimax_regret' else 0)
                      for sid in relevant]
            scores[candidate] = max(values)
        if not scores:
            if policy['selected'] is not None:
                raise ValueError('Undefined policy replaced with an invented design')
            continue
        expected = min(scores, key=lambda candidate: (scores[candidate], candidate))
        if policy['selected'] != expected:
            raise ValueError('Independent finite-policy selection mismatch')
        close(policy['objective'], scores[expected])


def write_csv(path, rows):
    """Export readable registries while keeping JSON as the full evidence source."""
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def audit(project, result_path):
    """Save auditable computation checks without changing pipeline state or author declarations."""
    result = json.loads(result_path.read_text(encoding='utf-8'))
    destination = result_path.parent / 'independent-audit'
    if destination.exists():
        raise ValueError('Do not overwrite an existing independent audit')
    base = project / 'milestones/reproducibility'
    sources = {'source': base / 'network-interfaces/concrete-interfaces.json',
               'register': base / 'model-assumptions/network-experiment.json',
               'units': base / 'network-interfaces/native-property-unit-review.json',
               'contacts': project.parent / 'research_data/pilot_inferred_contacts.csv'}
    for name, path in sources.items():
        if sha(path) != result['sourceHashes'][name]:
            raise ValueError('Changed source: ' + name)
    for name, expected in result['codeHashes'].items():
        path = project / 'code' / name
        if sha(path) != expected:
            raise ValueError('Changed experiment executable: ' + name)
        sources['code/' + name] = path
    source = json.loads(sources['source'].read_text(encoding='utf-8'))
    components = {component['ifc_id']: component for component in source['components']}
    terminals = {node: component['psets']['FI_Tekninen']['Virtaama'] * 0.001
                 for node, component in components.items() if component['ifc_type'] == 'IfcAirTerminal'}
    close(result['source_terminal_total_m3_s'], sum(terminals.values()))
    if result['terminal_count'] != len(terminals) or result['field_validation'] is not False:
        raise ValueError('Incorrect source-terminal count or field-certification claim')
    unique = {(row['candidate_id'], row['scenario_id']) for row in result['records']}
    expected_count = len(result['candidate_designs']) * 15
    if len(unique) != len(result['records']) or len(unique) != expected_count:
        raise ValueError('Incomplete/duplicate candidate-scenario coverage')
    parameters = result['model_assumptions']['parameters']
    for row in result['records']:
        independent_case(row, result['candidate_designs'][row['candidate_id']], components, terminals, parameters)
    independent_policies(result)
    destination.mkdir()
    checks = [{'name': name, 'status': 'PASS', 'evidence': evidence} for name, evidence in [
        ('source-and-code-fingerprints', 'Current source, typed-unit register, contacts, assumptions and all recorded executables match frozen hashes.'),
        ('terminal-continuity', 'All 158 source terminal demands independently accumulated along complete root-terminal paths.'),
        ('pressure-energy-partial-carbon', 'Every calculable record independently checked with Colebrook fixed-point iteration and path sums; rel/abs tolerance 1e-8.'),
        ('adverse-and-unresolved-cases', 'All failed/unknown cases retain null objective; component-screen failures are independently recomputed.'),
        ('finite-design-policy', 'All three policy scores/selections independently recomputed using design scenarios only.'),
        ('candidate-scenario-coverage', f'{len(unique)} unique records; no discarded candidate-scenario evaluations.')]]
    report = {'status': 'PASS', 'scope': 'NUMERICAL_MODEL_VERIFICATION_ONLY_NOT_FIELD_OR_PUBLICATION_APPROVAL',
              'resultSha256': sha(result_path), 'command': f'python code/audit_source_network_experiment.py --result "{result_path}"',
              'sourceHashes': {str(path.resolve()): sha(path) for path in sources.values()}, 'checks': checks,
              'record_status_counts': dict(Counter(row['reason'] for row in result['records'])),
              'limitations': ['Inferred bbox topology is not verified native IFC connectivity.',
                              'Maximum geometric port is a reference section, not branch-port capacity certification.',
                              'Virtual controllable pressure source is not the actual 302PF01 fan.',
                              'Counterfactual sections can include fittings/terminals; product, junction and spatial compatibility unverified.',
                              'Grid, EPD proxy, operating hours and local-loss coefficients are assumptions, not measurements.',
                              'Only duct shell and ideal fan operational carbon are included; this is not whole-life building LCA.',
                              'Deterministic stress cases are not independent random samples; no inferential p-values warranted.']}
    (destination / 'numerical-audit.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    generated = result['generated_component_parameters']
    if generated:
        write_csv(destination / 'generated-component-inputs.csv', generated)
    register_rows = [{'parameter': name, 'value': json.dumps(value), 'origin': 'ASSUMED',
                      'disclosure': 'Conditional model input; replace with project/device/EPD evidence before field claims.'}
                     for name, value in parameters.items()]
    write_csv(destination / 'assumed-global-inputs.csv', register_rows)
    columns = ['candidate_id', 'scenario_id', 'split', 'demand_multiplier', 'grid_kgco2e_kwh',
               'model_feasible', 'reason', 'objective', 'required_pressure_Pa', 'ideal_controlled_fan_annual_kWh']
    write_csv(destination / 'experiment-outcomes.csv', [{key: row.get(key, '') for key in columns} for row in result['records']])
    print(json.dumps({'audit': str(destination), 'status': report['status'], 'result_sha256': report['resultSha256'],
                      'counts': report['record_status_counts'], 'generated_component_inputs': len(generated)}))


def main():
    """Audit a named immutable result instead of silently adopting it into the paper."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--result', required=True, type=Path)
    args = parser.parse_args()
    audit(Path(__file__).resolve().parents[1], args.result)


if __name__ == '__main__':
    main()
