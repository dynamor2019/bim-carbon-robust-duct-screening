import copy,unittest
from validate_native_rvt_connectors import validate


def fixture():
    rows=[]
    for a,b in ((1,2),(2,1)):
        rows.append({'owner_id':a,'connector_id':0,'domain':'DomainHvac','connector_type':'End','is_connected':True,
            'origin_internal_ft':[0.,0.,0.],'all_refs':[{'owner_id':b,'connector_id':0,'domain':'DomainHvac','connector_type':'End'}]})
    return {'artifact_type':'native_RVT_HVAC_connector_export','source_sha256_before':'a'*64,'source_sha256_after':'a'*64,
        'host_version':'2024','coordinate_basis':'REVIT_INTERNAL_FEET_NO_PROJECT_OR_MAP_TRANSFORM','status':'EXTRACTED_REQUIRES_VALIDATION','failures':[],'rows':rows}

class ConnectorTests(unittest.TestCase):
    def test_reciprocal_records_do_not_certify_service(self):
        result=validate(fixture()); self.assertFalse(result['errors']); self.assertFalse(result['physical_service_certified'])
    def test_missing_target_and_reverse_block(self):
        report=fixture(); report['rows'].pop()
        self.assertIn('HVAC_REFERENCE_TARGET_NOT_EXPORTED',validate(report)['errors'])
        report=fixture(); report['rows'][1]['all_refs']=[]
        self.assertIn('NONRECIPROCAL_REFERENCE',validate(report)['errors'])
    def test_hash_duplicates_and_extraction_failures_block(self):
        report=fixture(); report['source_sha256_after']='b'*64
        self.assertIn('SOURCE_HASH_UNBOUND_OR_CHANGED',validate(report)['errors'])
        report=fixture(); report['rows'].append(copy.deepcopy(report['rows'][0]))
        self.assertIn('DUPLICATE_CONNECTOR_ID',validate(report)['errors'])
        report=fixture(); report['failures']=[{'error':'SOFTWARE_ONLY'}]
        self.assertIn('EXTRACTION_FAILURES_OR_STATUS',validate(report)['errors'])
    def test_logical_self_refs_remain_warnings(self):
        report=fixture(); report['rows'][0]['all_refs'].append({'owner_id':1,'connector_id':1,'domain':'DomainHvac','connector_type':'Logical'})
        self.assertIn('SELF_OWNER_REFERENCE_RETAINED',validate(report)['warnings'])

if __name__=='__main__': unittest.main()
