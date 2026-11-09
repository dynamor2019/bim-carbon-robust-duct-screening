"""Locate network boundary ambiguities from immutable pilot evidence, never certify edges."""
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def components(nodes, edges):
    adjacency = {n: set() for n in nodes}
    for a, b in edges:
        if a in adjacency and b in adjacency:
            adjacency[a].add(b)
            adjacency[b].add(a)
    remaining, groups = set(nodes), []
    while remaining:
        root = min(remaining)
        todo, visited = [root], set()
        while todo:
            n = todo.pop()
            if n in visited:
                continue
            visited.add(n)
            todo.extend(adjacency[n] - visited)
        remaining -= visited
        groups.append(sorted(visited))
    return sorted(groups, key=lambda x: (-len(x), x[0]))


def box_gap(row, box):
    return math.sqrt(sum(max(float(row[f'bbox_min_{axis}_m']) - box['max_m'][i],
                             box['min_m'][i] - float(row[f'bbox_max_{axis}_m']), 0.) ** 2
                         for i, axis in enumerate('xyz')))


def main():
    project = Path(__file__).resolve().parents[1]
    raw = project.parent / 'research_data'
    boundary_path = project / 'milestones/reproducibility/boundary-evidence/source-boundary.json'
    paths = [raw / 'pilot_components_enriched.csv', raw / 'pilot_inferred_contacts.csv', boundary_path]
    pilot, contacts = rows(paths[0]), rows(paths[1])
    boundary = json.loads(boundary_path.read_text(encoding='utf-8'))
    output = project / 'milestones/reproducibility/boundary-evidence'
    reports, ledger, balance_rows = [], [], []
    for model in boundary['models']:
        name = model['model_id']
        indexed = {r['ifc_id']: r for r in pilot if r['model_id'] == name and r['system_name'] == '302PK01 (toimistot, oikea)'}
        contact_rows = [r for r in contacts if r['model_id'] == name]
        graph_reports = []
        for tolerance in sorted({float(r['tolerance_m']) for r in contact_rows}):
            # Separate each recorded tolerance instead of merging into a false trusted graph.
            edges = {tuple(sorted((r['component_a'], r['component_b']))) for r in contact_rows if float(r['tolerance_m']) == tolerance}
            group_reports = []
            for group_index, group in enumerate(components(indexed, edges)):
                members = [indexed[n] for n in group]
                terms = [r for r in members if r['ifc_type'] == 'IfcAirTerminal']
                q = sum(float(r['flow_rate_raw']) for r in terms if r['flow_rate_raw'])
                group_reports.append({'component_index': group_index, 'node_count': len(group),
                    'class_counts': dict(Counter(r['ifc_type'] for r in members)),
                    'terminal_count': len(terms), 'raw_terminal_flow_sum': q,
                    'floors': dict(Counter(r['floor'] for r in members)),
                    'terminal_ids': sorted(r['ifc_id'] for r in terms),
                    'min_z_m': min(float(r['bbox_min_z_m']) for r in members),
                    'max_z_m': max(float(r['bbox_max_z_m']) for r in members)})
                for r in members:
                    ledger.append({'model_id': name, 'tolerance_m': tolerance,
                        'candidate_component_index': group_index, 'ifc_id': r['ifc_id'],
                        'ifc_guid': r['ifc_guid'], 'ifc_type': r['ifc_type'], 'floor': r['floor'],
                        'raw_flow': r['flow_rate_raw'], 'classification': 'candidate_component_not_verified_network'})
            graph_reports.append({'tolerance_m': tolerance, 'unique_edges': len(edges), 'groups': group_reports})
        adjacency = {node: set() for node in indexed}
        for r in contact_rows:
            if float(r['tolerance_m']) == .005 and r['component_a'] in indexed and r['component_b'] in indexed:
                adjacency[r['component_a']].add(r['component_b'])
                adjacency[r['component_b']].add(r['component_a'])
        for node, r in indexed.items():
            if r['ifc_type'] != 'IfcDuctFitting':
                continue
            # Only direct segment neighbors, no assumed traversal through other fittings.
            neighbors = [indexed[n] for n in sorted(adjacency[node]) if indexed[n]['ifc_type'] == 'IfcDuctSegment']
            values = [float(n['flow_rate_raw']) for n in neighbors if n['flow_rate_raw'] and float(n['flow_rate_raw']) > 0]
            residual = None
            category = 'insufficient_or_ambiguous_neighbors'
            if len(values) == len(neighbors) and len(values) in (2, 3):
                residual = abs(2 * max(values) - sum(values))
                category = 'raw_magnitudes_compatible' if residual <= 1e-8 else 'raw_magnitudes_incompatible'
            balance_rows.append({'model_id': name, 'ifc_id': node, 'name': r['name'], 'floor': r['floor'],
                'candidate_direct_segment_count': len(neighbors),
                'candidate_direct_segment_ids': '|'.join(n['ifc_id'] for n in neighbors),
                'raw_positive_flows': '|'.join(str(v) for v in values),
                'magnitude_balance_residual_raw': residual, 'screening': category,
                'evidence_level': 'bbox_neighbors_not_native_ports; compatibility_does_not_certify_topology_or_direction'})
        box = model['fan']['geometry']
        near = []
        for r in indexed.values():
            gap = box_gap(r, box)
            if gap <= .5:
                near.append({'ifc_id': r['ifc_id'], 'ifc_type': r['ifc_type'], 'name': r['name'],
                    'floor': r['floor'], 'bbox_gap_m': gap, 'raw_flow': r['flow_rate_raw'],
                    'diameter_m': r['diameter_m'], 'width_m': r['width_m'], 'height_m': r['height_m'],
                    'total_pressure_raw': r['total_pressure_raw'],
                    'bbox_min_m': [float(r[f'bbox_min_{a}_m']) for a in 'xyz'],
                    'bbox_max_m': [float(r[f'bbox_max_{a}_m']) for a in 'xyz']})
        ducts = [r for r in indexed.values() if r['ifc_type'] == 'IfcDuctSegment' and r['flow_rate_raw']]
        highest = sorted(ducts, key=lambda r: (-float(r['flow_rate_raw']), r['ifc_id']))[:20]
        terms = [r for r in indexed.values() if r['ifc_type'] == 'IfcAirTerminal']
        guid_counts = Counter(r['ifc_guid'] for r in terms)
        coord_counts = Counter(tuple(float(r[f'centroid_{a}_m']) for a in 'xyz') for r in terms)
        separated_boundaries = []
        base_graph = graph_reports[0]
        if len(base_graph['groups']) > 1:
            base_tolerance = base_graph['tolerance_m']
            base_edges = {tuple(sorted((r['component_a'], r['component_b']))) for r in contact_rows if float(r['tolerance_m']) == base_tolerance}
            base_groups = components(indexed, base_edges)
            main_nodes = base_groups[0]
            for group_index, group in enumerate(base_groups[1:], 1):
                candidates = []
                for a in group:
                    ra = indexed[a]
                    for b in main_nodes:
                        rb = indexed[b]
                        box_b = {'min_m': [float(rb[f'bbox_min_{axis}_m']) for axis in 'xyz'],
                                 'max_m': [float(rb[f'bbox_max_{axis}_m']) for axis in 'xyz']}
                        gap = box_gap(ra, box_b)
                        candidates.append((gap, a, b))
                nearest = []
                for gap, a, b in sorted(candidates)[:12]:
                    ra, rb = indexed[a], indexed[b]
                    paired = []
                    for r in pilot:
                        if r['model_id'] != name and r['ifc_guid'] in {ra['ifc_guid'], rb['ifc_guid']}:
                            paired.append({'model_id': r['model_id'], 'ifc_id': r['ifc_id'], 'guid': r['ifc_guid'],
                                'floor': r['floor'], 'raw_flow': r['flow_rate_raw']})
                    nearest.append({'island_id': a, 'main_id': b, 'bbox_gap_m': gap,
                        'island_type': ra['ifc_type'], 'main_type': rb['ifc_type'],
                        'island_floor': ra['floor'], 'main_floor': rb['floor'],
                        'island_raw_flow': ra['flow_rate_raw'], 'main_raw_flow': rb['flow_rate_raw'],
                        'paired_guid_matches': paired,
                        'status': 'diagnostic_proximity_only_do_not_add_edge'})
                separated_boundaries.append({'candidate_component_index': group_index,
                    'nearest_bbox_pairs_to_main': nearest})
        reports.append({'model_id': name, 'graphs_by_tolerance': graph_reports,
            'separated_component_boundary_candidates': separated_boundaries,
            'equipment_nearby_05m': sorted(near, key=lambda r: (r['bbox_gap_m'], r['ifc_id'])),
            'flow_balance_screening_counts': dict(Counter(r['screening'] for r in balance_rows if r['model_id'] == name)),
            'highest_raw_flow_ducts': [{k: r[k] for k in ['ifc_id', 'floor', 'flow_rate_raw', 'diameter_m', 'width_m', 'height_m', 'total_pressure_raw', 'centroid_x_m', 'centroid_y_m', 'centroid_z_m']} for r in highest],
            'duplicate_terminal_guids': {k:v for k,v in guid_counts.items() if v>1},
            'exact_duplicate_terminal_centroids': [{'centroid': list(k), 'count': v} for k,v in coord_counts.items() if v>1],
            'note': 'All flow values are raw; bbox proximity does not identify AHU ports or confirm service; 0.5m is a search window only, not engineering clearance.'})
    result = {'status': 'REQUIRES_REVIEW', 'artifact_type': 'candidate_boundary_diagnostic',
        'sourceHashes': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        'codeSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'models': reports}
    (output / 'network-boundary.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='')
    with (output / 'candidate-components.csv').open('w', encoding='utf-8', newline='') as stream:
        writer=csv.DictWriter(stream, fieldnames=list(ledger[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(ledger)
    with (output / 'candidate-flow-balance.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(balance_rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(balance_rows)
    compact = [{'model_id':m['model_id'], 'graphs': [{'tolerance_m':g['tolerance_m'],
         'groups':[{k:r[k] for k in ['node_count','terminal_count','raw_terminal_flow_sum','floors']} for r in g['groups']]} for g in m['graphs_by_tolerance']],
         'nearby_count':len(m['equipment_nearby_05m']), 'top_flows': sorted({float(r['flow_rate_raw']) for r in m['highest_raw_flow_ducts']}, reverse=True),
         'duplicates':m['duplicate_terminal_guids'], 'duplicate_coords':m['exact_duplicate_terminal_centroids']} for m in reports]
    print(json.dumps(compact, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
