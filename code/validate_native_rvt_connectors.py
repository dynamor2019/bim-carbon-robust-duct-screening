"""Validate native connector export records; no graph/service certification."""
import math,re


def validate(report):
    errors=[]; warnings=[]
    if report.get('artifact_type')!='native_RVT_HVAC_connector_export': errors.append('WRONG_ARTIFACT_TYPE')
    before=report.get('source_sha256_before'); after=report.get('source_sha256_after')
    if not isinstance(before,str) or not re.fullmatch('[0-9a-f]{64}',before) or before!=after: errors.append('SOURCE_HASH_UNBOUND_OR_CHANGED')
    if report.get('host_version')!='2024': errors.append('UNVALIDATED_HOST_VERSION')
    if report.get('coordinate_basis')!='REVIT_INTERNAL_FEET_NO_PROJECT_OR_MAP_TRANSFORM': errors.append('UNSUPPORTED_COORDINATE_BASIS')
    if report.get('status')!='EXTRACTED_REQUIRES_VALIDATION' or report.get('failures'): errors.append('EXTRACTION_FAILURES_OR_STATUS')
    rows=report.get('rows'); index={}
    if not isinstance(rows,list) or not rows: errors.append('EMPTY_OR_INVALID_CONNECTOR_SET'); rows=[]
    for r in rows:
        key=(r.get('owner_id'),r.get('connector_id'))
        if any(type(x)!=int or x<0 for x in key): errors.append('INVALID_CONNECTOR_ID'); continue
        if key in index: errors.append('DUPLICATE_CONNECTOR_ID')
        index[key]=r
        origin=r.get('origin_internal_ft')
        if not isinstance(origin,list) or len(origin)!=3 or not all(type(x) in (int,float) and math.isfinite(x) for x in origin): errors.append('INVALID_ORIGIN')
        if r.get('domain')!='DomainHvac': errors.append('NON_HVAC_EXPORTED_ROW')
        if not isinstance(r.get('all_refs'),list): errors.append('INVALID_REFERENCE_LIST')
    for key,row in index.items():
        if not isinstance(row.get('all_refs'),list): continue
        physical_refs=[]
        seen=set()
        for ref in row['all_refs']:
            target=(ref.get('owner_id'),ref.get('connector_id'))
            if any(type(x)!=int or x<0 for x in target): errors.append('INVALID_REFERENCE_ID'); continue
            if target in seen: errors.append('DUPLICATE_REFERENCE')
            seen.add(target)
            if target[0]==key[0]: warnings.append('SELF_OWNER_REFERENCE_RETAINED'); continue
            if ref.get('domain')!='DomainHvac' or ref.get('connector_type')=='Logical' or row.get('connector_type')=='Logical':
                warnings.append('LOGICAL_OR_OTHER_DOMAIN_REFERENCE_RETAINED'); continue
            physical_refs.append(target)
            if target not in index: errors.append('HVAC_REFERENCE_TARGET_NOT_EXPORTED'); continue
            other=index[target]
            reverse=other.get('all_refs')
            if not isinstance(reverse,list) or key not in {(r.get('owner_id'),r.get('connector_id')) for r in reverse}: errors.append('NONRECIPROCAL_REFERENCE')
        if physical_refs and row.get('is_connected') is not True: errors.append('REFERENCE_WITH_DISCONNECTED_FLAG')
        if row.get('is_connected') is True and not physical_refs: warnings.append('CONNECTED_WITHOUT_EXTERNAL_PHYSICAL_REF')
    return {'status':'BLOCKED_CONNECTOR_EXPORT_INTEGRITY' if errors else 'PASS_CONNECTOR_RECORD_INTEGRITY_ONLY',
        'errors':errors,'warnings':warnings,'connector_count':len(rows),'physical_service_certified':False,
        'limitations':['No IFC/RVT identity mapping, coordinate registration, direction applicability or fan/terminal service certified.',
            'External nonlogical HVAC AllRefs are candidates; reference reciprocity is not independent as-built connection proof.']}
