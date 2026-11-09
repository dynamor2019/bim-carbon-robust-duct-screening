"""Declared exploratory perturbations; never infer population probabilities."""

from datetime import datetime, timezone

from scipy.stats import qmc

MISSING_IDS = (611084, 611151, 3680435, 3680544, 3681026)
SOURCES = {
    'sensitivity': 'https://publications.jrc.ec.europa.eu/repository/handle/JRC122132',
    'interactions': 'https://publications.jrc.ec.europa.eu/repository/handle/JRC114437',
    'ducts': 'https://handbook.ashrae.org/Handbooks/F25/SI/F25_Ch21/F25_Ch21_si.aspx',
    'sampling': 'https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.LatinHypercube.html',
    'verification': 'https://www.grc.nasa.gov/WWW/wind/valid/tutorial/overview.html',
}


def factor_definitions():
    """Separate handbook-supported roughness from illustrative stress bounds."""
    factors = [{'name': f'dimension_{identifier}', 'low': 0.12, 'nominal': 0.16,
                'high': 0.20, 'unit': 'm', 'origin': 'ILLUSTRATIVE_PLUS_MINUS_25_PERCENT'}
               for identifier in MISSING_IDS]
    for name, low, nominal, high, unit in (
        ('efficiency', 0.5, 0.6, 0.7, 'fraction'),
        ('hours_per_year', 2000, 2500, 3000, 'h/year'),
        ('roughness_m', 0.00005, 0.00009, 0.00015, 'm'),
        ('wall_thickness_m', 0.0005, 0.0007, 0.001, 'm'),
        ('duct_production_kgco2e_kg', 2.1, 2.8, 3.5, 'kgCO2e/kg'),
        ('local_loss_multiplier', 0.5, 1.0, 1.5, 'fraction'),
    ):
        origin = ('ROUNDED_GALVANIZED_DUCT_HANDBOOK_RANGE_NOT_SOURCE_CALIBRATION'
                  if name == 'roughness_m' else 'ILLUSTRATIVE_ENGINEERING_STRESS_RANGE')
        factors.append(dict(name=name, low=low, nominal=nominal, high=high, unit=unit, origin=origin))
    return factors


def make_protocol():
    """Freeze all 89 variants before evaluating outcomes, including interactions."""
    factors = factor_definitions()
    nominal = {factor['name']: factor['nominal'] for factor in factors}
    variants = [dict(id='nominal', kind='nominal', factors=nominal)]
    for factor in factors:
        for endpoint in ('low', 'high'):
            variants.append(dict(id=f"{factor['name']}_{endpoint}", kind='one_at_a_time',
                                 factors=dict(nominal, **{factor['name']: factor[endpoint]})))
    for endpoint in ('low', 'high'):
        variants.append(dict(id='joint_' + endpoint, kind='joint_corner',
                             factors={factor['name']: factor[endpoint] for factor in factors}))
    sampler = qmc.LatinHypercube(d=len(factors), rng=20261007)
    samples = qmc.scale(sampler.random(64), [f['low'] for f in factors], [f['high'] for f in factors])
    for index, sample in enumerate(samples):
        variants.append(dict(id=f'lhs_{index:02d}', kind='joint_latin_hypercube',
                             factors={factor['name']: float(value) for factor, value in zip(factors, sample)}))
    return dict(schema_version=1, created_at=datetime.now(timezone.utc).isoformat(),
                author_choice='A: retain direction and add evidence', factors=factors, variants=variants,
                sources=SOURCES, seed=20261007, analysis='EXPLORATORY_BOUNDED_SCREENING_NOT_GLOBAL_SOBOL',
                bounds_status='Not confidence intervals, measured inputs or product qualification',
                topology='Original inferred edges retained; no native-port validation invented',
                arms={'fixed': 'Freeze candidate edges and designed sizes; replace only unresolved source placeholders',
                      'regenerated': 'Regenerate routes and sizing when placeholder inputs change; labels may denote new geometry'},
                selection='D0-D2 only; held-out cases never select candidates',
                reporting='Report all reversals, failures, unknowns and null objectives; no favorable tuning')
