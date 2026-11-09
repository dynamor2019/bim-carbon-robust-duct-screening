"""Resolve supported IFC typed-measure units, including project inheritance."""
import math

PREFIX={None:1.,'DECI':.1,'CENTI':.01,'MILLI':.001,'MICRO':1e-6,'KILO':1000.,'MEGA':1e6}
MEASURE={'IfcVolumetricFlowRateMeasure':'VOLUMETRICFLOWRATEUNIT','IfcLinearVelocityMeasure':'LINEARVELOCITYUNIT',
    'IfcLengthMeasure':'LENGTHUNIT','IfcPositiveLengthMeasure':'LENGTHUNIT','IfcNonNegativeLengthMeasure':'LENGTHUNIT'}


def scale_to_si(unit):
    kind=unit['type']
    if kind=='IfcSIUnit':
        prefix=PREFIX[unit.get('Prefix')]
        name=unit['Name']
        if name in ('METRE','SQUARE_METRE','CUBIC_METRE'):
            return prefix**{'METRE':1,'SQUARE_METRE':2,'CUBIC_METRE':3}[name]
        if name=='SECOND':
            return prefix
        if name=='GRAM':
            return .001*prefix
        raise ValueError('Unsupported SI base unit for this audit: '+name)
    if kind=='IfcDerivedUnit':
        value=math.prod(scale_to_si(element['Unit'])**element['Exponent'] for element in unit['Elements'])
        if not math.isfinite(value) or value<=0:
            raise ValueError('Invalid derived unit scale')
        return value
    raise ValueError('Unsupported unit class for this audit: '+kind)


def resolve_property(property_record,assigned_units):
    expected=MEASURE.get(property_record.get('nominal_value_type'))
    explicit=property_record.get('explicit_unit')
    if expected is None:
        return None
    candidates=[explicit] if explicit is not None else [unit for unit in assigned_units if unit.get('UnitType')==expected]
    if len(candidates)!=1 or candidates[0].get('UnitType')!=expected:
        raise ValueError('Typed unit context absent, ambiguous or incompatible')
    return {'measure_type':property_record['nominal_value_type'],'unit_type':expected,
        'scale_to_SI':scale_to_si(candidates[0]),'basis':'PROPERTY_OVERRIDE' if explicit is not None else 'TYPED_PROJECT_UNIT_INHERITANCE'}
