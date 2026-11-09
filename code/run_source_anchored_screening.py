"""Execute a disclosed fixed-route physics screen; never replace the formal routing experiment."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from source_anchored_physics import pressure_loss, validate_assumptions

__all__ = ['extract_segments', 'evaluate', 'run']


def sha(path):
    """Bind results to exact source and executable bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_segments(source):
    """Preserve source design values, recording unsupported/zero/missing records separately."""
    if source.get('length_unit_scale_to_m') != 0.001:
        raise ValueError('Expected audited millimetre source geometry')
    if source.get('sourceSha256') != source.get('sourceSha256_after'):
        raise ValueError('Source extraction was not read-only')
    included, excluded = [], []
    for component in source['components']:
        if component['ifc_type'] != 'IfcDuctSegment':
            continue
        geometry = component['psets'].get('FI_Geometria', {})
        technical = component['psets'].get('FI_Tekninen', {})
        fields = [geometry.get('Halkaisija'), geometry.get('Pituus'), technical.get('Virtaama')]
        if not all(type(v) in (int, float) and v > 0 for v in fields):
            excluded.append({'ifc_id': component['ifc_id'], 'source_values': fields,
                             'reason': 'noncircular_or_nonpositive_or_missing_source_field'})
            continue
        included.append({'ifc_id': component['ifc_id'], 'guid': component['guid'],
                         'diameter_m': fields[0] * 0.001, 'length_m': fields[1] * 0.001,
                         'design_flow_m3_s': fields[2] * 0.001,
                         'source_pressure_Pa': technical.get('Painehäviö'),
                         'source_velocity_m_s': technical.get('Virtausnopeus'),
                         'origin': 'IFC_DESIGN_PROPERTIES_NOT_MEASUREMENTS'})
    if not included:
        raise ValueError('No positive circular source segments; no invented case fallback')
    return included, excluded


def evaluate(segment, parameters, multiplier):
    """Compute explicit assumption-dependent straight-loss quantities, not complete fan energy."""
    flow = segment['design_flow_m3_s'] * multiplier
    row = pressure_loss(flow, segment['length_m'], segment['diameter_m'], parameters)
    row.update(ifc_id=segment['ifc_id'], flow_multiplier=multiplier,
               flow_m3_s=flow, source_origin=segment['origin'],
               assumption_origin='GENERATED_EXPERIENCE_ASSUMPTIONS')
    if row['pressure_Pa'] is not None:
        work = flow * row['pressure_Pa']
        equivalent = work / parameters['efficiency'] * parameters['hours_per_year'] / 1000
        row.update(straight_dissipation_W=work, allocated_electricity_proxy_kWh=equivalent,
                   allocated_B6_proxy_kgCO2e=equivalent * parameters['grid_kgco2e_kwh'])
    else:
        row.update(straight_dissipation_W=None, allocated_electricity_proxy_kWh=None,
                   allocated_B6_proxy_kgCO2e=None)
    shell = math_shell_mass(segment, parameters)
    row['assumed_shell_mass_kg'] = shell
    return row


def math_shell_mass(segment, parameters):
    """Use an explicitly assumed thin shell, excluding fittings, insulation and supports."""
    diameter, thickness = segment['diameter_m'], parameters['wall_thickness_m']
    area = math.pi * ((diameter + 2 * thickness) ** 2 - diameter ** 2) / 4
    return area * segment['length_m'] * parameters['steel_density_kg_m3']


def write_csv(path, rows):
    """Write reproducible rectangular tables without silently dropping unknown values."""
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def scenarios(register):
    """Predeclare one-at-a-time bounds without pretending to sample field uncertainty."""
    nominal = validate_assumptions(register['parameters'])
    yield 'nominal', nominal
    for name, record in register['parameters'].items():
        for label, value in zip(('low', 'high'), record['range']):
            modified = {key: dict(item) for key, item in register['parameters'].items()}
            modified[name]['value'] = value
            yield name + '_' + label, validate_assumptions(modified)


def run(project, destination):
    """Bind source and assumptions before calculation and retain every excluded input."""
    source_path = project / 'milestones/reproducibility/network-interfaces/concrete-interfaces.json'
    register_path = project / 'milestones/reproducibility/model-assumptions/source-screening.json'
    if destination.exists():
        raise ValueError('Use a new output directory; existing results are immutable')
    source = json.loads(source_path.read_text(encoding='utf-8'))
    register = json.loads(register_path.read_text(encoding='utf-8'))
    validate_assumptions(register['parameters'])
    if register['flow_unit'] != 'L/s' or register['source_sha256'] != sha(source_path):
        raise ValueError('Source/flow-unit assumption binding mismatch')
    unit_path = source_path.with_name('native-property-unit-review.json')
    units = json.loads(unit_path.read_text(encoding='utf-8'))
    if units['status'] != 'PASS_TYPED_UNIT_RESOLUTION' or units['inputHashes'][source_path.name] != sha(source_path):
        raise ValueError('Typed source unit review is stale or failed')
    segments, excluded = extract_segments(source)
    rows = []
    for scenario_id, parameters in scenarios(register):
        for multiplier in register['flow_multipliers']:
            if type(multiplier) not in (int, float) or not math.isfinite(multiplier) or multiplier <= 0:
                raise ValueError('Positive finite explicit flow multiplier required')
            for segment in segments:
                rows.append(dict(evaluate(segment, parameters, multiplier), scenario_id=scenario_id))
    destination.mkdir(parents=True)
    result = {'data_origin': 'SOURCE_ANCHORED_MODELLED_SCREENING',
              'model_id': source['model_id'], 'system_name': source['system_name'],
              'sourceSha256': sha(source_path), 'registerSha256': sha(register_path),
              'unitReviewSha256': sha(unit_path),
              'codeHashes': {name: sha(Path(__file__).with_name(name)) for name in
                             ('run_source_anchored_screening.py', 'source_anchored_physics.py')},
              'source_segments': segments, 'excluded_source_segments': excluded,
              'records': rows, 'formal_route_size_optimization_completed': False,
              'field_validation': False, 'fan_operating_energy': None,
              'limitations': ['Fixed source routes and diameters; no routing or sizing policy optimization.',
                              'Straight segment losses only; no fitting/terminal losses, balance or fan operating point.',
                              'Allocated electricity/carbon proxies are not actual fan energy or complete system B6.',
                              'All assumed inputs and demand scenarios require sensitivity and real-data replacement.']}
    path = destination / 'source-screening-results.json'
    path.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    write_csv(destination / 'source-segments.csv', segments)
    write_csv(destination / 'modelled-screening.csv', rows)
    write_csv(destination / 'generated-parameter-register.csv', [dict(parameter=name, **record)
              for name, record in register['parameters'].items()])
    print(json.dumps({'source_segments': len(segments), 'excluded': len(excluded),
                      'records': len(rows), 'result_sha256': sha(path), 'result_file': str(path)}))
    return result


def main():
    """Require an explicit destination, leaving active manuscript and workflow bindings untouched."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    run(Path(__file__).resolve().parents[1], args.output_dir)


if __name__ == '__main__':
    main()
