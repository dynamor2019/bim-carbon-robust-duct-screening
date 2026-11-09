"""Independent equation checks, not field validation or engineering certification."""

import math

from scipy.optimize import brentq

from source_anchored_physics import pressure_loss
from source_network_model import flows


def reference_loss(flow, length, diameter, parameters):
    """Solve Colebrook with SciPy Brent instead of the production bisection."""
    velocity = 4 * flow / (math.pi * diameter ** 2)
    reynolds = velocity * diameter / parameters['kinematic_viscosity_m2_s']
    if 2300 <= reynolds < 4000:
        return None
    if reynolds < 2300:
        dynamic_viscosity = parameters['density_kg_m3'] * parameters['kinematic_viscosity_m2_s']
        return 128 * dynamic_viscosity * length * flow / (math.pi * diameter ** 4)
    def residual(inverse_sqrt):
        """Return the independent Colebrook residual."""
        return inverse_sqrt + 2 * math.log10(
            parameters['roughness_m'] / (3.7 * diameter) + 2.51 * inverse_sqrt / reynolds)
    inverse_sqrt = brentq(residual, 1, 30, xtol=1e-12)
    return length * parameters['density_kg_m3'] * velocity ** 2 / (2 * diameter * inverse_sqrt ** 2)


def benchmark(parameters, candidates, terminals):
    """Check 54 equation cases and actual rectangular velocity adapters."""
    rows = []
    for diameter in (0.1, 0.3, 1.0):
        for length in (1, 10, 100):
            for reynolds in (500, 2000, 3000, 10000, 100000, 1000000):
                flow = reynolds * parameters['kinematic_viscosity_m2_s'] * math.pi * diameter / 4
                actual = pressure_loss(flow, length, diameter, parameters)['pressure_Pa']
                expected = reference_loss(flow, length, diameter, parameters)
                error = abs(actual - expected) / expected if expected is not None else None
                rows.append(dict(diameter=diameter, length=length, reynolds=reynolds,
                                 actual=actual, reference=expected, relative_error=error))
                if (actual is None) != (expected is None) or (error is not None and error > 1e-10):
                    raise ValueError('Independent pressure equation check failed')
    adapter_count, worst_adapter, worst_continuity = 0, 0.0, 0.0
    for candidate in candidates.values():
        loads = flows(candidate['tree'], terminals)
        root = next(node for node in candidate['tree'] if candidate['tree'].in_degree(node) == 0)
        worst_continuity = max(worst_continuity, abs(loads[root] - sum(terminals.values())))
        for node, size in candidate['sizes'].items():
            if size['origin'] != 'DERIVED_SOURCE_RECTANGULAR_HYDRAULIC_DIAMETER':
                continue
            velocity = loads[node] / size['area']
            equivalent_flow = velocity * math.pi * size['diameter'] ** 2 / 4
            recovered = 4 * equivalent_flow / (math.pi * size['diameter'] ** 2)
            worst_adapter = max(worst_adapter, abs(velocity - recovered))
            adapter_count += 1
    if worst_adapter > 1e-10 or worst_continuity > 1e-10:
        raise ValueError('Adapter or root continuity check failed')
    return dict(status='PASS_EQUATION_VERIFICATION_ONLY', pressure_cases=rows,
                rectangular_adapter_count=adapter_count, max_adapter_error_m_s=worst_adapter,
                max_root_continuity_error_m3_s=worst_continuity,
                physical_validation=False, noncircular_physical_error_bound=None,
                limitation='Agreement with the same equations is not agreement with measured duct behavior')
