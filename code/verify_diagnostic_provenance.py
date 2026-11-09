"""Reject stale input/code hashes across the current diagnostic evidence set."""
import json
from pathlib import Path
from recover_fitting_interfaces import sha

ARTIFACTS={
    'network-interfaces/independent-interface-audit.json':'audit_network_interfaces.py',
    'network-interfaces/terminal-dimension-review.json':'qualify_terminal_geometry.py',
    'network-interfaces/terminal-joint-candidates.json':'screen_terminal_joint_candidates.py',
    'network-interfaces/rectangular-interface-review.json':'recover_rectangular_interfaces.py',
    'network-interfaces/pipe-length-loss-review.json':'audit_pipe_geometry_losses.py',
    'network-interfaces/rectangular-native-context.json':'trace_rectangular_context.py',
    'network-interfaces/profile-type-audit.json':'audit_profile_curve_types.py',
    'network-interfaces/mixed-section-review.json':'screen_mixed_interfaces.py',
    'network-interfaces/mixed-flow-context.json':'audit_mixed_flow_context.py',

    'network-interfaces/native-property-unit-review.json':'audit_ifc_property_units.py',
    'network-interfaces/flow-unit-review.json':'audit_flow_units.py',
    'network-interfaces/terminal-service-review.json':'audit_terminal_service.py',
    'network-interfaces/terminal-service-validation.json':'validate_terminal_service.py',
    'parameter-evidence/prl-interface-review.json':'inspect_prl_interfaces.py',
    'architecture-source-index.json':'fetch_architecture_sources.py',
    'architecture-space-inventory.json':'inventory_architecture_spaces.py',
    'architecture-frame-review.json':'compare_architecture_frames.py',
    'upper-floor-spatial-review.json':'screen_upper_floor_spaces.py',
    'upper-floor-mesh-audit.json':'audit_upper_floor_meshes.py',
    'upper-floor-boundary-diagnosis.json':'diagnose_upper_floor_boundaries.py',
    'architecture-declaration-audit.json':'audit_architecture_declarations.py',
    'native-face-coverage-audit.json':'audit_native_face_coverage.py',
    'upper-storey-native-scope-audit.json':'audit_upper_storey_native_scope.py',
    'upper-storey-hole-coverage-audit.json':'audit_upper_storey_hole_coverage.py',
    'equipment-reference-label-audit.json':'audit_equipment_reference_labels.py',
    'fan-schedule-identity-audit.json':'audit_fan_schedule_identity.py',
    'equipment-anchor-candidate-audit.json':'audit_equipment_anchor_candidates.py',
    'ahu-designation-schedule-review.json':'audit_ahu_designation_schedule.py',
    'alignment-marker-review.json':'audit_alignment_markers.py',
    'alignment-registration-audit.json':'audit_alignment_registration.py',
    'AHU-neighborhood-interface-audit.json':'audit_AHU_neighborhood_interfaces.py',
    'AHU-rim-offset-review.json':'audit_AHU_rim_offsets.py',
    'AHU-native-gap-source-audit.json':'audit_AHU_native_gap_sources.py',
    'engineering-input-gate.json':'guard_engineering_inputs.py',
    'protocol-amendment-binding.json':'record_protocol_amendment_binding.py',
    'synthetic-data/synthetic-input-sanity.json':'run_synthetic_route_size.py',
    'synthetic-data/data-validation.json':'validate_synthetic_benchmark.py',
    'synthetic-data/statistical-audit.json':'validate_synthetic_benchmark.py',
    'synthetic-data/reproduction-check.json':'validate_synthetic_benchmark.py',
    'synthetic-data/synthetic-summary.json':'validate_synthetic_benchmark.py',
    'synthetic-data/synthetic-table-audit.json':'milestones/reproducibility/assemble_display_fragments.py',
    'statistical-audit.json':'validate_synthetic_benchmark.py',
    'reproduction-check.json':'validate_synthetic_benchmark.py',
    'local-spatial-domain-freeze.json':'generate_local_spatial_domain.py',
    'local-spatial-domain-software-audit.json':'test_local_spatial_domain.py',
    'local-spatial-mesh-check.json':'check_local_spatial_mesh.py',
    'spatial-contract-software-audit.json':'test_spatial_comparison_contract.py',
    'finite-decision-software-audit.json':'verify_finite_decision_software.py',
    'candidate-tree-software-audit.json':'verify_candidate_tree_software.py',
    'candidate-evaluation-preflight.json':'evaluate_candidate_design.py',
    'scenario-wrapper-software-audit.json':'verify_scenario_wrapper_software.py',
    'delivered-HVAC-source-review.json':'audit_delivered_HVAC_sources.py',
    'duct-material-table-audit.json':'audit_duct_material_table.py',
    'native-duct-material-audit.json':'audit_native_duct_materials.py',
    'duct-size-specification-audit.json':'audit_duct_size_specification.py',
    'duct-dimension-consistency-audit.json':'audit_duct_dimension_consistency.py',
    'modelling-qualification-audit.json':'audit_modelling_qualifications.py',
    'whole-IFC-connectivity-audit.json':'audit_whole_ifc_connectivity.py',
    'native-RVT-runtime-preflight.json':'inspect_native_rvt_runtime.py',
    'native-RVT-exporter-software-audit.json':'verify_native_rvt_exporter.py',
    'engineering-blocker-triage.json':'triage_engineering_blockers.py',
    'engineering-gate-consistency-audit.json':'audit_engineering_gate_consistency.py',
    'halton-pra-source-review.json':'verify_halton_pra_sources.py',
    'halton-pra-formula-ocr.json':'ocr_halton_pra_formula.py',
    'halton-pra-object-audit.json':'audit_halton_pra_objects.py',
    'halton-pts-source-review.json':'audit_halton_pts_sources.py',
    'halton-pts-native-unit-audit.json':'audit_halton_pts_native_units.py',
    'engineering-parameter-unlock-checklist.json':'build_engineering_unlock_checklist.py',
    'parameter-evidence/lindab-reference-catalogue.json':'qualify_lindab_catalogue.py',
}


def main():
    project=Path(__file__).resolve().parents[1]
    root=project/'milestones/reproducibility'
    folders=[root,root/'network-interfaces',root/'parameter-evidence',project/'.dsh-state/parameter-cache']
    errors=[]
    records=[]
    for relative,script in ARTIFACTS.items():
        path=root/relative
        data=json.loads(path.read_text(encoding='utf-8'))
        checks=[]
        for helper,expected in data.get('helperHashes',{}).items():
            if sha(project/'code'/helper)!=expected:
                errors.append(relative+': helper hash differs: '+helper)
        for model in data.get('models',[]):
            for mesh in model.get('cached_mesh_inputs',[]):
                mesh_path=Path(mesh['path'])
                valid=mesh_path.exists() and sha(mesh_path)==mesh['sha256']
                checks.append({'input':str(mesh_path),'status':'PASS' if valid else 'FAIL'})
                if not valid:
                    errors.append(relative+': cached mesh hash differs: '+str(mesh_path))
        producer_path=project/script if '/' in script else project/'code'/script
        if data.get('codeSha256')!=sha(producer_path):
            errors.append(relative+': code hash differs')
        if 'unitHelperSha256' in data and data['unitHelperSha256']!=sha(project/'code/resolve_ifc_units.py'):
            errors.append(relative+': unit helper hash differs')
        if 'polygonHolesHelperSha256' in data and data['polygonHolesHelperSha256']!=sha(project/'code/polygon_holes.py'):
            errors.append(relative+': polygon holes helper hash differs')
        if 'nativeSpaceHelperSha256' in data and data['nativeSpaceHelperSha256']!=sha(project/'code/native_space_geometry.py'):
            errors.append(relative+': native space helper hash differs')
        if 'polygonGeometryHelperSha256' in data and data['polygonGeometryHelperSha256']!=sha(project/'code/polygon_geometry.py'):
            errors.append(relative+': polygon geometry helper hash differs')
        if 'polygonHelperSha256' in data and data['polygonHelperSha256']!=sha(project/'code/native_polygon_audit.py'):
            errors.append(relative+': native polygon helper hash differs')
        if 'diagnosticHelperSha256' in data and data['diagnosticHelperSha256']!=sha(project/'code/mesh_diagnostics.py'):
            errors.append(relative+': diagnostic helper hash differs')
        if 'meshHelperSha256' in data and data['meshHelperSha256']!=sha(project/'code/mesh_containment.py'):
            errors.append(relative+': mesh helper hash differs')
        if 'transportHelperSha256' in data and data['transportHelperSha256']!=sha(project/'code/fetch_http_range.ps1'):
            errors.append(relative+': HTTP transport helper hash differs')
        for source in data.get('selected_sources',[])+data.get('source_files',[]):
            source_path=Path(source['path'])
            actual=sha(source_path)
            source_name=source.get('name',str(source_path))
            checks.append({'input':source_name,'sha256':actual,'pass':actual==source['sha256']})
            if actual!=source['sha256']:
                errors.append(relative+': downloaded source differs: '+source_name)
        for name,expected in data.get('inputHashes',{}).items():
            candidates=[folder/name for folder in folders if (folder/name).is_file()]
            if len(candidates)!=1:
                errors.append(relative+': input path absent or ambiguous: '+name)
                continue
            actual=sha(candidates[0])
            checks.append({'input':name,'sha256':actual,'pass':actual==expected})
            if actual!=expected:
                errors.append(relative+': stale input: '+name)
        if relative.endswith('profile-type-audit.json'):
            for model,material in zip(data['models'],['concrete','timber']):
                current=sha(root/'network-interfaces'/(material+'-interfaces.json'))
                checks.append({'input':material+'-interfaces.json','sha256':current,'pass':current==model['inventory_sha256']})
                if current!=model['inventory_sha256']:
                    errors.append(relative+': stale profile inventory')
        records.append({'artifact':relative,'sha256':sha(path),'code':script,'input_checks':checks})
    report={'artifact_type':'current_diagnostic_hash_sync_audit','status':'FAIL' if errors else 'PASS_DIAGNOSTIC_HASH_SYNC_ONLY',
        'codeSha256':sha(Path(__file__)),'errors':errors,'artifacts':records,
        'scope':'Current diagnostic dependencies and code bindings only; does not set formal result provenance VERIFIED.',
        'formal_experiment_gate':'ORIGINAL_REAL_ENGINEERING_ONLY: BLOCKED. Active synthetic qualification is in separate result-specific validation reports; this hash-only audit does not certify either branch.'}
    target=root/'diagnostic-provenance-audit.json'
    if target.exists():
        history=project/'.dsh-state/diagnostic-audit-history';history.mkdir(parents=True,exist_ok=True)
        (history/(sha(target)+'.json')).write_bytes(target.read_bytes())
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':report['status'],'artifact_count':len(records),'input_checks':sum(len(r['input_checks']) for r in records),
        'errors':errors,'formal_experiment_gate':report['formal_experiment_gate']},indent=2))
    if errors:
        raise SystemExit(2)


if __name__=='__main__':
    main()
