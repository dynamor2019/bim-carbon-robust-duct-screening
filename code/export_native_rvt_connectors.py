# -*- coding: utf-8 -*-
"""Run inside pyRevit/Revit 2024 on an already-open original office model.
No transaction, document save, model upgrade or engineering inference.
IronPython-compatible host program; CPython cannot execute Autodesk API.
"""
import os
import json
import hashlib
from datetime import datetime


def file_sha(path):
    digest=hashlib.sha256()
    with open(path,'rb') as stream:
        while True:
            block=stream.read(1024*1024)
            if not block: break
            digest.update(block)
    return digest.hexdigest()


def id_value(value):
    try: return int(value.Value)
    except AttributeError: return int(value.IntegerValue)


def extract(doc,source_path,output_path):
    from Autodesk.Revit.DB import FilteredElementCollector,Domain
    if doc.IsFamilyDocument or doc.IsModified:
        raise ValueError('Require an unmodified original project document')
    if os.path.normcase(os.path.abspath(doc.PathName))!=os.path.normcase(os.path.abspath(source_path)):
        raise ValueError('Active document path differs from declared original RVT')
    if not doc.Application.VersionNumber=='2024':
        raise ValueError('Only declared source-compatible Revit 2024 host authorized by this exporter')
    before=file_sha(source_path)
    rows=[]; failures=[]
    for element in FilteredElementCollector(doc).WhereElementIsNotElementType():
        try:
            manager=getattr(element,'ConnectorManager',None)
            if manager is None:
                mep=getattr(element,'MEPModel',None)
                manager=getattr(mep,'ConnectorManager',None) if mep else None
            if manager is None: continue
            for connector in manager.Connectors:
                if connector.Domain!=Domain.DomainHvac: continue
                def optional(name):
                    try:
                        value=getattr(connector,name)
                        return str(value) if name in ('Direction','ConnectorType','Shape') else value
                    except Exception:
                        return None
                refs=[]
                for ref in connector.AllRefs:
                    refs.append({'owner_id':id_value(ref.Owner.Id),'connector_id':int(ref.Id),
                        'domain':str(ref.Domain),'connector_type':str(ref.ConnectorType)})
                origin=connector.Origin
                system=optional('MEPSystem')
                rows.append({'owner_id':id_value(element.Id),'owner_unique_id':element.UniqueId,
                    'owner_name':element.Name,'connector_id':int(connector.Id),'domain':str(connector.Domain),
                    'connector_type':optional('ConnectorType'),'shape':optional('Shape'),
                    'direction':optional('Direction'),'is_connected':bool(connector.IsConnected),
                    'origin_internal_ft':[origin.X,origin.Y,origin.Z],
                    'system_id':id_value(system.Id) if system else None,'system_name':system.Name if system else None,
                    'flow_internal_ft3_s':optional('Flow'),'radius_internal_ft':optional('Radius'),
                    'width_internal_ft':optional('Width'),'height_internal_ft':optional('Height'),
                    'all_refs':refs})
        except Exception as exc:
            failures.append({'owner_id':id_value(element.Id),'error':str(exc)})
    after=file_sha(source_path)
    if before!=after or doc.IsModified:
        raise ValueError('Original disk hash or in-memory modified state changed')
    report={'artifact_type':'native_RVT_HVAC_connector_export','status':'EXTRACTION_WITH_FAILURES' if failures else 'EXTRACTED_REQUIRES_VALIDATION',
        'source_path':source_path,'source_sha256_before':before,'source_sha256_after':after,
        'host_version':doc.Application.VersionNumber,'host_build':doc.Application.VersionBuild,
        'coordinate_basis':'REVIT_INTERNAL_FEET_NO_PROJECT_OR_MAP_TRANSFORM',
        'unit_conversions_declared':{'length_ft_to_m':.3048,'flow_ft3_s_to_m3_s':.3048**3},
        'created_utc':datetime.utcnow().isoformat()+'Z','rows':rows,'failures':failures,
        'code_sha256':file_sha(__file__),'physical_service_certified':False,'formal_experiment':False,
        'limitations':['AllRefs includes logical/self/non-HVAC references; raw references retained and must be classified.',
            'Connector Direction and Flow are model declarations, not measured actual operation.',
            'RVT UniqueId is not asserted to equal exported IFC GlobalId; explicit mapping required.',
            'No transformations, fan selection, graph repair or engineering feasibility inferred.']}
    if os.path.exists(output_path):
        raise ValueError('Refuse overwrite of an existing raw connector export')
    with open(output_path,'w') as stream:
        json.dump(report,stream,ensure_ascii=True,indent=2,allow_nan=False)
    return report


if __name__=='__main__':
    # Set environment variables in the host session before execution; never guess source.
    source=os.environ.get('DSH_RVT_SOURCE')
    output=os.environ.get('DSH_RVT_CONNECTOR_OUTPUT')
    project=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    allowed=os.path.normcase(os.path.abspath(os.path.join(project,'.dsh-state','native-rvt-connectors')))+os.sep
    if not source or not output or not os.path.normcase(os.path.abspath(output)).startswith(allowed):
        raise ValueError('Explicit original source and in-project raw-export path required')
    source_root=os.path.join(os.path.dirname(project),'extracted','HVAC','MAGICAD-FOR-REVIT')
    authorized_sources=[os.path.normcase(os.path.abspath(os.path.join(source_root,'HVAC_NordicLCA_Office_'+variant+'_BuildingPermit.rvt'))) for variant in ('Concrete','Timber')]
    if not source or os.path.normcase(os.path.abspath(source)) not in authorized_sources:
        raise ValueError('Require exact delivered original office RVT path')
    directory=os.path.dirname(output)
    if not os.path.isdir(directory): os.makedirs(directory)
    extract(__revit__.ActiveUIDocument.Document,source,output)
