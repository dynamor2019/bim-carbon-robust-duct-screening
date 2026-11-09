"""Straight circular duct calculations on source design data, not field measurements."""

import math

__all__ = ['pressure_loss', 'validate_assumptions']


def validate_assumptions(parameters):
    """Reject unregistered, nonfinite or physically impossible assumed inputs."""
    required = {'density_kg_m3', 'kinematic_viscosity_m2_s', 'roughness_m',
                'efficiency', 'hours_per_year', 'grid_kgco2e_kwh',
                'wall_thickness_m', 'steel_density_kg_m3'}
    if set(parameters) != required:
        raise ValueError('Exact assumption parameter set required')
    for name, record in parameters.items():
        if record.get('origin') != 'ASSUMED' or not record.get('rationale'):
            raise ValueError('Missing assumption disclosure: ' + name)
        value = record.get('value')
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError('Positive finite assumption required: ' + name)
    if parameters['efficiency']['value'] > 1:
        raise ValueError('Efficiency cannot exceed one')
    if parameters['hours_per_year']['value'] > 8760:
        raise ValueError('Annual hours exceed an ordinary year')
    return {name: record['value'] for name, record in parameters.items()}


def pressure_loss(flow, length, diameter, parameters):
    """Use Darcy-Weisbach and an implicit Colebrook solve; retain transitional cases."""
    if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0
           for v in (flow, length, diameter)):
        raise ValueError('Positive finite SI source values required')
    velocity = flow / (math.pi * diameter ** 2 / 4)
    reynolds = velocity * diameter / parameters['kinematic_viscosity_m2_s']
    if 2300 <= reynolds < 4000:
        return {'status': 'UNRESOLVED_TRANSITIONAL_FLOW', 'reynolds': reynolds,
                'velocity_m_s': velocity, 'pressure_Pa': None}
    if reynolds < 2300:
        friction = 64 / reynolds
    else:
        low, high = 1.0, 30.0
        residual = lambda y: y + 2 * math.log10(
            parameters['roughness_m'] / diameter / 3.7 + 2.51 * y / reynolds)
        if residual(low) * residual(high) > 0:
            raise ValueError('Colebrook root is outside numerical bracket')
        for _ in range(60):
            middle = (low + high) / 2
            if residual(middle) > 0:
                high = middle
            else:
                low = middle
        friction = ((low + high) / 2) ** -2
    pressure = friction * length / diameter * parameters['density_kg_m3'] * velocity ** 2 / 2
    return {'status': 'MODELLED_STRAIGHT_LOSS', 'velocity_m_s': velocity,
            'reynolds': reynolds, 'darcy_factor': friction, 'pressure_Pa': pressure}
