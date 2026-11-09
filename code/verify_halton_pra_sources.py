"""Record bounded official Halton PRA URL search; no performance parameter extraction."""
import json
from pathlib import Path
from guard_engineering_inputs import sha

if __name__=='__main__':
    project=Path(__file__).resolve().parents[1]
    cache=project/'.dsh-state/manufacturer-cache/halton-pra'
    acquisition=json.loads((cache/'acquisition.json').read_text(encoding='utf-8'))
    if sha(cache/'official-product.json')!=acquisition['raw_sha256'] or sha(cache/'official-product.txt')!=acquisition['text_sha256']:
        raise ValueError('Manufacturer raw/text hash mismatch')
    evidence=[project/'milestones/reproducibility/delivered-HVAC-source-review.json',cache/'official-product.json',cache/'official-product.txt',cache/'acquisition.json',project/'code/acquire_halton_pra.py']
    technical=json.loads((cache/'technical-acquisition.json').read_text(encoding='utf-8'))
    if sha(Path(technical['pdf_path']))!=technical['pdf_sha256']: raise ValueError('Technical PDF changed')
    evidence.extend([cache/'technical-acquisition.json',cache/'official-PRA-fr.pdf',cache/'official-flow-formula.jpg',project/'code/acquire_halton_pra_technical.py'])
    for page in technical['extracted_pages']:
        if sha(Path(page['path']))!=page['sha256']: raise ValueError('PDF extracted page changed')
        evidence.append(Path(page['path']))
    evidence.extend([project/'milestones/reproducibility/halton-pra-formula-ocr.json',cache/'official-PRA-fr-page005-poppler.txt',project/'code/ocr_halton_pra_formula.py'])
    report={'technical_document':{'url':technical['url'],'physical_pages':technical['page_count'],'printed_identifier':'20/PRA/0620/FR','formula_status':'UNVERIFIED_OPERATOR_OCR_AND_POPPLER_INCOMPLETE','text_evidence':{'page':5,'lines':[207,225],'claim':'Measurement tap differential pressure, k depends installation size and setting; qv in l/s.'},'performance_graphs':'PRA pages7-9 present, not digitized or numerically adopted','historical_applicability':'Identifier retained; not proof of delivered 2024 project product revision'},'artifact_type':'Halton_PRA_manufacturer_source_review','status':'OFFICIAL_PRA_MEASUREMENT_SOURCE_AVAILABLE_NOT_CASE_QUALIFIED','codeSha256':sha(Path(__file__)),'source_files':[{'path':str(p),'sha256':sha(p)} for p in evidence],
        'official_page':acquisition['official_page'],'official_api':acquisition['official_api'],'manufacturer_modified_gmt':acquisition['modified_gmt'],
        'verified_evidence':[{'text_lines':[112,113],'claim':'Total pressure loss increases as iris aperture closes; airflow measured at differential pressure taps.'},{'text_lines':[135,182],'claim':'Direction/installation restrictions, 4D upstream and 1D downstream in undisturbed straight duct; size/position-dependent measurement k-factor and correction factors.'}],
        'prior_search_status':'NO_VERIFIED_PRA_SELECTION_DATA from prior narrow URLs is superseded by official API discovery; 404 observation remains true for attempted URL.',
        'official_urls':[{'url':'https://www.halton.com/productgroup/airflow-management-dampers-and-controllers/','finding':'official airflow management group checked'}, {'url':'https://www.halton.com/products/halton-rmk-airflow-management-damper-cav/','finding':'related RMK CAV page; not PRA equivalence'}, {'url':'https://www.halton.com/products/halton-pra-airflow-management-damper/','finding':'HTTP 404 at checked URL'}],
        'project_source':'Office_concrete_Ventilation_Network components_20240611.pdf physical page 4 lists Halton PRA regulating damper.',
        'unresolved':['Measurement k-factor and measurement tap pressure are not adopted as local loss K or total device pressure drop; exact formula rendered graphically not transcribed from missing text.','Project schedule does not bind installed PRA to native object, setting, route or 302PF01 service path.','No RMK or generic coefficient transferred.'],'formal_experiment':False}
    out=project/'milestones/reproducibility/halton-pra-source-review.json'; out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline=''); print(json.dumps({'status':report['status'],'source_count':len(report['official_urls'])},indent=2))
