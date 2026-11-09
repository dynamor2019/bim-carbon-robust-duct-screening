"""Produce review tables from traced IFC evidence; no physical connection inferred."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


def main():
    project = Path(__file__).resolve().parents[1]
    folder = project / 'milestones/reproducibility/boundary-evidence'
    source = folder / 'source-boundary.json'
    terminals_path = folder / 'terminal-properties.json'
    boundary = json.loads(source.read_text(encoding='utf-8'))
    terminals = json.loads(terminals_path.read_text(encoding='utf-8'))
    table, summaries = [], []
    for model in boundary['models']:
        inventory = model['all_ifc_fan_inventory']
        for row in inventory:
            code = row['component'].get('Laitetunnus', '')
            common = row['component'].get('04 Komponentin yleisnimi', '')
            groups = [g['group_name'] for g in row['group_memberships']]
            table.append({'model_id': model['model_id'], 'ifc_id': row['ifc_id'], 'guid': row['guid'],
                'ifc_class': 'IfcFan', 'name': row['name'], 'device_identifier': code,
                'component_common_name': common, 'assigned_groups': '|'.join(groups),
                'is_302_group_member': any(g.startswith('302PK01') for g in groups),
                'review_status': 'semantic_membership_observed_physical_service_unverified'})
        selected = [r for r in terminals if r['model_id'] == model['model_id']]
        by_floor = defaultdict(lambda: {'count': 0, 'raw_flow_sum': 0., 'pressure_missing': 0})
        mismatches = []
        classifications = Counter()
        for row in selected:
            tech = row['psets'].get('FI_Tekninen', {})
            flow = tech.get('Virtaama')
            classifications[row['psets'].get('FI_Komponentti', {}).get('04 Komponentin yleisnimi', '<missing>')] += 1
            stats = by_floor[row['floor']]
            stats['count'] += 1
            stats['raw_flow_sum'] += float(row['raw_flow'])
            stats['pressure_missing'] += tech.get('Painehäviö') is None
            if flow is None or abs(float(row['raw_flow']) - float(flow)) > 1e-9:
                mismatches.append(row['ifc_id'])
        assert sum(v['count'] for v in by_floor.values()) == model['terminal_count']
        assert abs(sum(v['raw_flow_sum'] for v in by_floor.values()) - model['raw_flow_sum']) < 1e-9
        summaries.append({'model_id': model['model_id'], 'ifc_fan_entity_count': len(inventory),
            'equipment_identifiers_starting_302_in_ifc_fan_inventory':
                [r['ifc_id'] for r in inventory if r['component'].get('Laitetunnus', '').startswith('302')],
            'terminal_component_classification': dict(classifications),
            'terminal_raw_flow_vs_ifc_property_mismatches': mismatches,
            'terminal_by_floor': dict(sorted(by_floor.items())),
            'terminal_geometry_spot_checks': model.get('terminal_geometry_spot_checks', []),
            'note': 'Raw terminal pressure attributes may aid model checks; not certified terminal requirements. No row was excluded to force equality with 3.6 m3/s.'})
    with (folder / 'equipment-review.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(table[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(table)
    result = {'status': 'REQUIRES_REVIEW', 'artifact_type': 'source_review_not_formal_experiment',
        'sourceHashes': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [source, terminals_path]},
        'codeSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'models': summaries}
    (folder / 'boundary-review.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='')
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
