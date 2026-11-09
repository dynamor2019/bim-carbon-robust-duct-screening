"""Read-only, source-located preflight audit; never an optimization experiment."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import platform
from collections import Counter, defaultdict
from pathlib import Path

MODEL_PREFIX = 'HVAC_NordicLCA_Office_'
SYSTEM = '302PK01 (toimistot, oikea)'


def number(value):
    """Keep missing distinct from zero and reject nonfinite input."""
    if value is None or str(value).strip() == '':
        return None
    result = float(value)
    if not math.isfinite(result):
        raise ValueError('nonfinite numeric input')
    return result


def section_area(row):
    """Use circular diameter or both rectangular dimensions, never bbox size."""
    d = number(row.get('diameter_m'))
    w, h = number(row.get('width_m')), number(row.get('height_m'))
    circular = d is not None and d > 0
    rectangular = w is not None and h is not None and w > 0 and h > 0
    if circular and rectangular:
        return None, 'ambiguous'
    if circular:
        return math.pi * d * d / 4, 'circular'
    if rectangular:
        return w * h, 'rectangular'
    return None, 'missing'


def flow_check(row):
    """Test L/s as a candidate unit only; do not certify source units."""
    q, v = number(row.get('flow_rate_raw')), number(row.get('velocity_raw'))
    area, shape = section_area(row)
    if q is None or v is None or area is None:
        return {'status': 'missing_or_ambiguous', 'section': shape}
    if q <= 0 or v <= 0:
        return {'status': 'nonpositive', 'section': shape}
    candidate = q / 1000
    predicted = v * area
    return {'status': 'evaluated', 'section': shape,
            'candidate_flow_m3_s': candidate, 'velocity_area_m3_s': predicted,
            'relative_error': abs(predicted - candidate) / candidate}


def load_csv(path):
    """Retain physical source record numbers, including multiline CSV fields."""
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        _ = reader.fieldnames  # Consume header before tracking first data line.
        output = []
        while True:
            start = reader.line_num + 1
            try:
                row = next(reader)
            except StopIteration:
                break
            row['_source_line'] = start
            output.append(row)
        return output


def sha(path):
    """Hash immutable evidence or program in streaming mode."""
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path, fields, rows):
    """Write canonical UTF-8 LF output."""
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n', extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def run(project, source):
    """Audit prerequisites without assigning unknown connections or factors."""
    names = ['components.csv', 'pilot_components_enriched.csv',
             'pilot_inferred_contacts.csv', 'physical_routing_demand_template.csv',
             'energy_parameter_template.csv', 'cost_carbon_factor_template.csv']
    paths = {name: source / name for name in names}
    before = {name: sha(path) for name, path in paths.items()}
    tables = {name: load_csv(path) for name, path in paths.items()}
    selected = lambda row: row.get('model_id', '').startswith(MODEL_PREFIX) and SYSTEM in row.get('system_name', '')
    components = [r for r in tables['components.csv'] if selected(r)]
    pilot = [r for r in tables['pilot_components_enriched.csv'] if selected(r)]
    demands = [r for r in tables['physical_routing_demand_template.csv'] if selected(r)]
    out = project / 'milestones' / 'reproducibility' / 'preflight'
    out.mkdir(parents=True, exist_ok=True)
    summaries, checks, review = [], [], []
    for model in sorted({r['model_id'] for r in components}):
        rows = [r for r in components if r['model_id'] == model]
        prows = [r for r in pilot if r['model_id'] == model]
        ds = [r for r in demands if r['model_id'] == model]
        ducts = [r for r in rows if r['ifc_type'] == 'IfcDuctSegment']
        terms = [r for r in rows if r['ifc_type'] == 'IfcAirTerminal']
        fans = [r for r in rows if r['ifc_type'] == 'IfcFan']
        evaluated = []
        for r in ducts:
            check = flow_check(r)
            checks.append(dict(model_id=model, component_key=r['component_key'], source_line=r['_source_line'], **check))
            if check['status'] == 'evaluated':
                evaluated.append(check['relative_error'])
        for r in ds:
            review.append({**r, 'review_class': 'unresolved',
                           'audit_note': 'Observed endpoint; source service, direction and validated demand require evidence.'})
        contacts = [r for r in tables['pilot_inferred_contacts.csv'] if r['model_id'] == model]
        unique = {tuple(sorted((r['component_a'], r['component_b']))) for r in contacts}
        ids = {r['ifc_id'] for r in prows}
        adjacency = {node: set() for node in ids}
        for a, b in unique:
            if a in ids and b in ids:
                adjacency[a].add(b)
                adjacency[b].add(a)
        remaining, sizes = set(ids), []
        while remaining:
            stack, visited = [next(iter(remaining))], set()
            while stack:
                node = stack.pop()
                if node in visited:
                    continue
                visited.add(node)
                stack.extend(adjacency[node] - visited)
            remaining -= visited
            sizes.append(len(visited))
        energies = [r for r in tables['energy_parameter_template.csv']
                    if r['model_id'] == model and r['system_name'] == SYSTEM]
        fields = ['source_equipment_guid', 'validated_flow_unit', 'validated_pressure_unit',
                  'fan_pump_efficiency', 'annual_operating_hours', 'electricity_price',
                  'electricity_carbon_factor', 'reference_study_period_years']
        summaries.append({'model_id': model, 'component_count': len(rows),
            'class_counts': dict(Counter(r['ifc_type'] for r in rows)),
            'pilot_count': len(prows), 'fans': [{'key': r['component_key'], 'guid': r['ifc_guid'],
            'name': r['name'], 'floor': r['floor'], 'source_line': r['_source_line'],
            'in_pilot': r['ifc_id'] in ids} for r in fans],
            'ducts': len(ducts), 'flow_area_evaluated': len(evaluated),
            'flow_area_median_candidate_relative_error': sorted(evaluated)[len(evaluated)//2] if evaluated else None,
            'flow_area_over_1pct': sum(e > .01 for e in evaluated),
            'terminals': len(terms), 'raw_terminal_flow_sum': sum(number(r['flow_rate_raw']) or 0 for r in terms),
            'raw_terminal_flow_sum_note': 'Raw field sum only; not a verified design demand or unit.',
            'demand_rows': len(ds),
            'demand_missing': {f: sum(not r.get(f, '').strip() for r in ds) for f in
                ['source_equipment_component_key', 'validated_design_flow_m3_s', 'flow_direction',
                 'required_terminal_pressure_pa', 'engineering_reference']},
            'contact_records': len(contacts), 'unique_undirected_candidate_contacts': len(unique),
            'candidate_graph_component_sizes': sorted(sizes, reverse=True),
            'candidate_graph_note': 'Union of recorded tolerances; no edge is certified by graph reachability.',
            'energy_missing': {f: not any(r.get(f, '').strip() for r in energies) for f in fields}})
    factors = [r for r in tables['cost_carbon_factor_template.csv'] if r['ifc_type'].startswith(('IfcDuct', 'IfcFan', 'IfcAirTerminal', 'IfcDamper'))]
    factor_missing = {f: sum(not r.get(f, '').strip() for r in factors) for f in
                      ['unit_cost', 'mass_per_m_kg', 'wall_thickness_m', 'epd_id',
                       'gwp_per_declared_unit', 'service_life_years', 'reference_url']}
    blockers = [
        {'id': 'B01', 'scope': 'topology_and_service', 'source': str(paths[names[3]]),
         'evidence': 'See per-model demand_missing; candidate contacts are not native ports.',
         'required': 'Evidence-backed source–branch–terminal ledger, direction, terminal flow units and pressure requirements.'},
        {'id': 'B02', 'scope': 'fan_geometry_and_efficiency', 'source': str(paths[names[0]]),
         'evidence': 'See fan records and in_pilot; energy efficiency/work-range fields need verification.',
         'required': 'Correct world-coordinate fan/interface geometry and documented performance/efficiency boundary; SFP cannot substitute.'},
        {'id': 'B03', 'scope': 'engineering_feasibility', 'source': str(project / 'milestones' / 'analysis-plan.md'),
         'evidence': 'Protocol sections 4.2 and 16 acknowledge missing obstacle models.',
         'required': 'Verified obstacle/alignment/installation rules or a documented scope amendment for a constrained analytical subproblem.'},
        {'id': 'B04', 'scope': 'quantity_cost_carbon', 'source': str(paths[names[5]]),
         'evidence': factor_missing,
         'required': 'Size-qualified mass/thickness, straight ducts, fittings and insulation quantities, applicable EPD, price and replacement sources.'},
        {'id': 'B05', 'scope': 'scenarios_and_protocol', 'source': str(project / 'milestones' / 'analysis-plan.md'),
         'evidence': 'Sections 3, 8 and 12 retain BLOCKED values and unsourced placeholder sensitivity ranges.',
         'required': 'Source-qualified design and held-out scenarios, objective choice, solver budget and corrected reporting/physical-model references.'}]
    report = {'status': 'BLOCKED', 'artifact_type': 'preflight_audit_not_formal_experiment',
        'source_directory': str(source), 'sourceHashes': before, 'programSha256': sha(Path(__file__)),
        'protocolSha256': sha(project / 'milestones' / 'analysis-plan.md'),
        'environment': {'python': platform.python_version(), 'platform': platform.platform()},
        'models': summaries, 'relevant_factor_rows': len(factors), 'factor_missing': factor_missing,
        'blockers': blockers, 'source_immutability': before == {n: sha(p) for n,p in paths.items()}}
    if not report['source_immutability']:
        raise RuntimeError('Source files changed during audit')
    write_csv(out / 'flow_section_checks.csv', ['model_id', 'component_key', 'source_line',
        'status', 'section', 'candidate_flow_m3_s', 'velocity_area_m3_s', 'relative_error'], checks)
    candidate_rows = [dict(r, review_class='inferred',
        engineering_confirmation='unverified', direction='unresolved')
        for r in tables['pilot_inferred_contacts.csv']
        if r['model_id'] in {s['model_id'] for s in summaries}]
    write_csv(out / 'connection_review.csv',
        list(tables['pilot_inferred_contacts.csv'][0]) +
        ['review_class', 'engineering_confirmation', 'direction'], candidate_rows)
    write_csv(out / 'terminal_review.csv', list(demands[0]) + ['review_class', 'audit_note'], review)
    (out / 'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'artifact_type': report['artifact_type'],
                      'models': summaries, 'factor_missing': factor_missing,
                      'source_immutability': report['source_immutability']}, ensure_ascii=False, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    run(project, args.source or project.parent / 'research_data')
