"""Trace existing IFC and device-schedule evidence without solving or inventing topology."""
from __future__ import annotations
import csv
import gc
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import fitz
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import ifcopenshell.util.unit
import numpy as np


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def simple(value):
    """Serialize original IFC values without discarding entity references."""
    if isinstance(value, ifcopenshell.entity_instance):
        if value.id() == 0 and hasattr(value, 'wrappedValue'):
            return {'type': value.is_a(), 'value': value.wrappedValue}
        return {'ifc_id': value.id(), 'ifc_type': value.is_a(), 'name': getattr(value, 'Name', None)}
    if isinstance(value, (tuple, list)):
        return [simple(x) for x in value]
    if isinstance(value, dict):
        return {k: simple(v) for k,v in value.items()}
    return value


def group_memberships(entity):
    """Group assignment is semantic membership, not a native physical connection."""
    return [{'relationship_id': r.id(), 'group_id': r.RelatingGroup.id(),
             'group_type': r.RelatingGroup.is_a(), 'group_name': r.RelatingGroup.Name}
            for r in getattr(entity, 'HasAssignments', ()) if r.is_a('IfcRelAssignsToGroup')]


def bbox(entity):
    """Re-extract actual world-coordinate vertices; no extra placement transform."""
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    shape = ifcopenshell.geom.create_shape(settings, entity)
    vertices = np.asarray(shape.geometry.verts, dtype=float).reshape((-1, 3))
    if not len(vertices) or not np.isfinite(vertices).all():
        raise ValueError('empty/nonfinite geometry')
    return {'min_m': vertices.min(axis=0).tolist(), 'max_m': vertices.max(axis=0).tolist(),
            'vertex_mean_m': vertices.mean(axis=0).tolist(), 'vertex_count': len(vertices),
            'note': 'World-coordinate tessellated bbox, not native ports or installation clearance.'}


def main():
    project = Path(__file__).resolve().parents[1]
    root = project.parent
    out = project / 'milestones' / 'reproducibility' / 'boundary-evidence'
    cache = project / '.dsh-state' / 'source-extracts'
    out.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    pdf = root / 'extracted' / 'HVAC' / 'Device-Schedule' / 'Office_concrete_HVAC_Device Schedule_20240611.pdf'
    doc = fitz.open(pdf)
    pages = []
    for page in (28, 31):
        text = doc[page - 1].get_text('text', sort=True)
        target = cache / f'office_schedule_page{page}.txt'
        target.write_text(text, encoding='utf-8', newline='')
        pages.append({'physical_page_1based': page, 'path': str(target), 'sha256': sha(target),
                      'extraction': 'PyMuPDF sorted text; table reading order not guaranteed'})
    doc.close()
    with (root / 'research_data' / 'components.csv').open(encoding='utf-8-sig', newline='') as stream:
        table = list(csv.DictReader(stream))
    with (root / 'research_data' / 'pilot_components_enriched.csv').open(encoding='utf-8-sig', newline='') as stream:
        pilot = {(r['model_id'], int(r['ifc_id'])): r for r in csv.DictReader(stream)}
    models = []
    source_hashes = {'device_schedule': sha(pdf), 'components.csv': sha(root / 'research_data' / 'components.csv'),
                     'pilot_components_enriched.csv': sha(root / 'research_data' / 'pilot_components_enriched.csv')}
    terminal_evidence = []
    for variant, fan_id in [('Concrete', 3305376), ('Timber', 3912298)]:
        model = f'HVAC_NordicLCA_Office_{variant}_BuildingPermit'
        path = root / 'extracted' / 'HVAC' / 'IFC' / (model + '.ifc')
        print('Inspecting', model, flush=True)
        source_hashes[model] = sha(path)
        source = ifcopenshell.open(str(path))
        fan = source.by_id(fan_id)
        rows = [r for r in table if r['model_id'] == model and r['system_name'] == '302PK01 (toimistot, oikea)']
        terminals = [r for r in rows if r['ifc_type'] == 'IfcAirTerminal']
        floor_flow, name_flow = defaultdict(float), defaultdict(float)
        for row in terminals:
            entity = source.by_id(int(row['ifc_id']))
            psets = ifcopenshell.util.element.get_psets(entity)
            terminal_evidence.append({'model_id': model, 'ifc_id': entity.id(), 'guid': entity.GlobalId,
                'name': entity.Name, 'floor': row['floor'], 'raw_flow': row['flow_rate_raw'],
                'group_memberships': group_memberships(entity), 'psets': simple(psets)})
            flow = float(row['flow_rate_raw']) if row['flow_rate_raw'] else 0
            floor_flow[row['floor']] += flow
            name_flow[row['name']] += flow
        try:
            geometry = {'status': 'EXTRACTED_BBOX_ONLY', **bbox(fan)}
        except Exception as error:
            geometry = {'status': 'FAILED', 'error': repr(error)}
        assignments = group_memberships(fan)
        group_counts = []
        for membership in assignments:
            members = [e for r in source.by_id(membership['group_id']).IsGroupedBy for e in r.RelatedObjects]
            group_counts.append({**membership, 'member_count': len(members),
                                 'class_counts': dict(Counter(e.is_a() for e in members))})
        fan_inventory = []
        for equipment in source.by_type('IfcFan'):
            epsets = ifcopenshell.util.element.get_psets(equipment)
            fan_inventory.append({'ifc_id': equipment.id(), 'guid': equipment.GlobalId,
                'name': equipment.Name, 'component': simple(epsets.get('FI_Komponentti', {})),
                'product': simple(epsets.get('FI_Tuote', {})),
                'location': simple(epsets.get('FI_Sijainti', {})),
                'group_memberships': group_memberships(equipment)})
        spot_checks, seen_floors = [], set()
        for row in terminals:
            if row['floor'] in seen_floors:
                continue
            seen_floors.add(row['floor'])
            entity = source.by_id(int(row['ifc_id']))
            psets = ifcopenshell.util.element.get_psets(entity)
            try:
                fresh = bbox(entity)
                old = pilot.get((model, entity.id()))
                differences = [abs(fresh[bound + '_m'][index] - float(old[f'bbox_{bound}_{axis}_m']))
                    for bound in ['min', 'max'] for index, axis in enumerate('xyz')] if old else []
                install = psets.get('FI_Asennus', {})
                upper = install.get('02 Komponentin yläpinnan korko, abs.')
                lower = install.get('04 Komponentin alapinnan korko, abs.')
                spot_checks.append({'ifc_id': entity.id(), 'floor': row['floor'], 'bbox': fresh,
                    'pilot_bbox_max_abs_error_m': max(differences) if differences else None,
                    'attribute_upper_m_candidate': upper * .001 if isinstance(upper, (int, float)) else None,
                    'attribute_lower_m_candidate': lower * .001 if isinstance(lower, (int, float)) else None,
                    'property_note': 'mm interpretation is tested as a candidate; attributes are not assumed identical to mesh surfaces.'})
            except Exception as error:
                spot_checks.append({'ifc_id': entity.id(), 'floor': row['floor'], 'status': 'FAILED', 'error': repr(error)})
        model_record = {'model_id': model, 'unit_scale_to_m': ifcopenshell.util.unit.calculate_unit_scale(source),
            'terminal_geometry_spot_checks': spot_checks,
            'all_ifc_fan_inventory': fan_inventory,
            'native_relationship_counts': {kind: len(source.by_type(kind)) for kind in
                ['IfcDistributionPort', 'IfcRelConnectsPorts', 'IfcRelConnectsPortToElement', 'IfcRelConnectsElements']},
            'fan': {'ifc_id': fan.id(), 'guid': fan.GlobalId, 'name': fan.Name,
                    'predefined_type': getattr(fan, 'PredefinedType', None),
                    'psets': simple(ifcopenshell.util.element.get_psets(fan)),
                    'group_memberships': assignments, 'assigned_group_contents': group_counts,
                    'geometry': geometry,
                    'direct_inverse_relationships': [{'ifc_id': r.id(), 'ifc_type': r.is_a(),
                        'related_object_count': len(getattr(r, 'RelatedObjects', ())),
                        'relating_group': simple(getattr(r, 'RelatingGroup', None)),
                        'relating_property_definition': simple(getattr(r, 'RelatingPropertyDefinition', None))}
                        for r in source.get_inverse(fan)]},
            'terminal_count': len(terminals), 'raw_flow_sum': sum(floor_flow.values()),
            'raw_flow_by_floor': dict(sorted(floor_flow.items())),
            'raw_flow_by_name': dict(sorted(name_flow.items())),
            'evidence_limit': 'Property/group evidence only; membership does not verify branch topology, flow units, fan curve or simultaneous service demand.'}
        models.append(model_record)
        del source, fan
        gc.collect()
    report = {'artifact_type': 'source_boundary_trace_not_optimization', 'status': 'REQUIRES_REVIEW',
        'sourceHashes': source_hashes, 'codeSha256': sha(Path(__file__)),
        'versions': {'ifcopenshell': ifcopenshell.version, 'pymupdf': fitz.VersionBind, 'numpy': np.__version__},
        'schedule_pages': pages, 'models': models}
    (out / 'source-boundary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='')
    (out / 'terminal-properties.json').write_text(json.dumps(terminal_evidence, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='')
    print(json.dumps({'models': [{'model_id': m['model_id'], 'unit_scale_to_m': m['unit_scale_to_m'],
          'native_relationship_counts': m['native_relationship_counts'], 'fan_bbox': m['fan']['geometry'],
          'fan_groups': m['fan']['group_memberships'], 'raw_flow_by_floor': m['raw_flow_by_floor']} for m in models]}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
