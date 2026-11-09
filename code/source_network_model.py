"""Conditional radial network model on real IFC components and inferred contacts."""

import csv
import math

import networkx as nx

from source_anchored_physics import pressure_loss

__all__ = ['build_graph', 'build_tree', 'prepare_dimensions', 'evaluate_tree', 'designs']


def positive(value):
    """Distinguish usable physical dimensions from missing/zero source values."""
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def prepare_dimensions(components):
    """Preserve known shapes; register missing hydraulic dimensions separately."""
    dimensions, assumptions = {}, []
    for identifier, component in components.items():
        g = component['psets'].get('FI_Geometria', {})
        diameter, width, height = [g.get(k, 0) * 0.001 for k in ('Halkaisija', 'Leveys', 'Korkeus')]
        radii = [radius for feature in component.get('features', [])
                 for radius in feature.get('radii_m', []) if positive(radius)]
        derived_port = not positive(diameter) and not (positive(width) and positive(height)) and bool(radii)
        if derived_port:
            diameter = 2 * max(radii)
        if positive(diameter):
            area, perimeter = math.pi * diameter ** 2 / 4, math.pi * diameter
            origin = 'SOURCE_MAX_GEOMETRIC_PORT_REFERENCE_NOT_NATIVE_CONNECTOR' if derived_port else 'SOURCE_NOMINAL_CIRCULAR_DIMENSION'
        elif positive(width) and positive(height):
            area, perimeter = width * height, 2 * (width + height)
            diameter, origin = 4 * area / perimeter, 'DERIVED_SOURCE_RECTANGULAR_HYDRAULIC_DIAMETER'
        else:
            diameter, area, perimeter = 0.16, math.pi * 0.16 ** 2 / 4, math.pi * 0.16
            origin = 'ASSUMED_MISSING_COMPONENT_DIMENSION'
            assumptions.append({'ifc_id': identifier, 'parameter': 'hydraulic_section',
                                'value': 0.16, 'unit': 'm', 'origin': origin,
                                'reason': 'Missing positive source shape; uniform modelling placeholder, not recovered product dimension.'})
        length = g.get('Pituus', 0) * 0.001
        if component['ifc_type'] == 'IfcDuctSegment' and not positive(length):
            length = math.dist(component['bbox_min_m'], component['bbox_max_m'])
            if not positive(length):
                raise ValueError('No source geometry for duct length: ' + str(identifier))
            assumptions.append({'ifc_id': identifier, 'parameter': 'length', 'value': length,
                                'unit': 'm', 'origin': 'SOURCE_BBOX_DIAGONAL_LENGTH_APPROXIMATION',
                                'reason': 'Bounding-box diagonal used only where positive source centreline length is missing.'})
        dimensions[identifier] = {'diameter': diameter, 'area': area, 'perimeter': perimeter,
                                  'length': max(length, 0), 'origin': origin}
    return dimensions, assumptions


def build_graph(components, contacts, model_id, tolerance, dimensions):
    """Use source-derived contacts as explicit topology assumptions, not native connectors."""
    graph = nx.Graph()
    graph.add_nodes_from(sorted(components))
    with contacts.open(encoding='utf-8', newline='') as stream:
        for row in csv.DictReader(stream):
            if row['model_id'] != model_id or float(row['tolerance_m']) != tolerance:
                continue
            a, b = int(row['component_a']), int(row['component_b'])
            if a not in components or b not in components or a == b:
                continue
            da, db = dimensions[a], dimensions[b]
            length = max((da['length'] + db['length']) / 2, 0.001)
            resistance = (da['length'] / da['diameter'] ** 5 + db['length'] / db['diameter'] ** 5) / 2
            graph.add_edge(a, b, length=length, resistance=max(resistance, 0.001))
    return graph


def build_tree(graph, root, mode, terminals):
    """Generate candidate paths with NetworkX; disconnected terminals are not silently dropped."""
    if mode == 'hop':
        paths = nx.single_source_shortest_path(graph, root)
    else:
        paths = nx.single_source_dijkstra_path(graph, root, weight=mode)
    missing = sorted(set(terminals) - set(paths))
    if missing:
        return None, missing
    tree = nx.DiGraph()
    tree.add_node(root)
    for identifier in sorted(terminals):
        path = paths[identifier]
        tree.add_edges_from(zip(path, path[1:]))
    if not nx.is_arborescence(tree):
        raise ValueError('Candidate paths did not form a unique radial network')
    return tree, []


def flows(tree, terminals):
    """Apply continuity to declared simultaneous source terminal design demands."""
    loads = {node: terminals.get(node, 0) for node in tree}
    for node in reversed(list(nx.topological_sort(tree))):
        loads[node] += sum(loads[child] for child in tree.successors(node))
    return loads


def designs(tree, terminals, dimensions, parameters, mode):
    """Declare finite sizing rules; expanded envelopes and catalogue are assumptions."""
    loads = flows(tree, terminals)
    catalogue = parameters['diameter_catalogue_m']
    sizes = {}
    for node in tree:
        source = dimensions[node]
        if mode == 'source' or source['origin'] == 'DERIVED_SOURCE_RECTANGULAR_HYDRAULIC_DIAMETER':
            sizes[node] = dict(source)
            continue
        eligible = [d for d in catalogue if loads[node] / (math.pi * d ** 2 / 4) <= parameters['velocity_limit_m_s']
                    and d <= source['diameter'] * parameters['envelope_expansion_ratio']]
        if not eligible:
            sizes[node] = dict(source)
            continue
        diameter = eligible[0] if mode == 'velocity' else eligible[min(1, len(eligible) - 1)]
        sizes[node] = dict(source, diameter=diameter, area=math.pi * diameter ** 2 / 4,
                           perimeter=math.pi * diameter, origin='MODELLED_COUNTERFACTUAL_DESIGN')
    return sizes


def local_pressure(component, flow, velocity, parameters):
    """Use source design pressure where calibratable; otherwise explicit class-level assumptions."""
    technical = component['psets'].get('FI_Tekninen', {})
    source_loss, source_velocity = technical.get('Painehäviö'), technical.get('Virtausnopeus')
    if positive(source_loss) and positive(source_velocity):
        return source_loss * (velocity / source_velocity) ** 2, 'SOURCE_DESIGN_LOSS_WITH_ASSUMED_VELOCITY_SQUARED_SCALING'
    coefficient = parameters['missing_local_loss_coefficients'][component['ifc_type']]
    return coefficient * parameters['density_kg_m3'] * velocity ** 2 / 2, 'ASSUMED_MISSING_LOCAL_LOSS'


def node_loss(identifier, flow, size, component, parameters):
    """Calculate one physical burden per traversed component, preserving unknown regimes."""
    velocity = flow / size['area']
    if component['ifc_type'] == 'IfcDuctSegment':
        # Hydraulic diameter uses the actual rectangular area, rather than circular-area substitution.
        equivalent_flow = velocity * math.pi * size['diameter'] ** 2 / 4
        result = pressure_loss(equivalent_flow, size['length'], size['diameter'], parameters)
        return result['pressure_Pa'], 'MODELLED_DARCY_STRAIGHT_LOSS'
    return local_pressure(component, flow, velocity, parameters)


def evaluate_tree(tree, sizes, components, terminals, parameters):
    """Evaluate conditional model feasibility and partial-stage carbon, not installed performance."""
    loads = flows(tree, terminals)
    losses, cumulative, details, mass = {}, {}, [], 0.0
    for node in nx.topological_sort(tree):
        size, component = sizes[node], components[node]
        loss, origin = node_loss(node, loads[node], size, component, parameters)
        if loss is None:
            return {'model_feasible': False, 'reason': 'UNRESOLVED_TRANSITIONAL_FLOW', 'objective': None}
        losses[node] = loss
        parent = next(tree.predecessors(node), None)
        cumulative[node] = loss + (cumulative[parent] if parent is not None else 0)
        velocity = loads[node] / size['area']
        if component['ifc_type'] == 'IfcDuctSegment':
            mass += size['perimeter'] * parameters['wall_thickness_m'] * size['length'] * parameters['steel_density_kg_m3']
        details.append({'ifc_id': node, 'flow_m3_s': loads[node], 'velocity_m_s': velocity,
                        'diameter_m': size['diameter'], 'pressure_loss_Pa': loss, 'loss_origin': origin,
                        'section_origin': size['origin'], 'parent': parent})
    failures = sum(row['velocity_m_s'] > parameters['velocity_limit_m_s']
                   for row in details if components[row['ifc_id']]['ifc_type'] != 'IfcAirTerminal')
    if failures:
        return {'model_feasible': False, 'reason': 'VELOCITY_SCREEN_FAILURE', 'objective': None,
                'failed_components': failures, 'components': details}
    root = next(node for node in tree if tree.in_degree(node) == 0)
    pressure = max(cumulative[terminal] for terminal in terminals)
    annual = loads[root] * pressure / parameters['efficiency'] * parameters['hours_per_year'] / 1000
    replacements = math.ceil(parameters['horizon_years'] / parameters['duct_lifetime_years']) - 1
    embodied = mass * parameters['duct_production_kgco2e_kg'] * (1 + replacements)
    operating = annual * parameters['horizon_years'] * parameters['grid_kgco2e_kwh']
    return {'model_feasible': True, 'reason': 'PASS_CONDITIONAL_RADIAL_MODEL_ONLY',
            'objective': embodied + operating, 'root_flow_m3_s': loads[root],
            'required_pressure_Pa': pressure, 'ideal_controlled_fan_annual_kWh': annual,
            'duct_shell_mass_kg': mass, 'duct_A1_A3_B4_kgco2e': embodied,
            'ideal_fan_B6_kgco2e': operating, 'components': details,
            'actual_engineering_feasible': None, 'actual_operating_energy_verified': False}
