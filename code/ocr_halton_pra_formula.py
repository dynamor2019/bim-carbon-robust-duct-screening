"""OCR original formula asset; OCR is candidate evidence, not visual verification."""
import json
from pathlib import Path
from rapidocr_onnxruntime import RapidOCR
from guard_engineering_inputs import sha

if __name__=='__main__':
    project=Path(__file__).resolve().parents[1]; folder=project/'.dsh-state/manufacturer-cache/halton-pra'
    image=folder/'official-flow-formula.jpg'
    engine=RapidOCR()
    result,timings=engine(str(image))
    records=[]
    for item in result or []:
        records.append({'box':item[0],'text':item[1],'ocr_confidence':float(item[2])})
    report={'artifact_type':'PRA_original_formula_OCR','status':'OCR_CANDIDATE_NOT_VISUALLY_VERIFIED','codeSha256':sha(Path(__file__)),'source_files':[{'path':str(image),'sha256':sha(image)}],
        'recognition':records,'timings':timings,'equation_adopted':False,'formal_experiment':False,
        'limitations':['OCR confidence is not mathematical correctness.','Subscripts, multiplication, radicals and pressure symbol must be checked against original image.','No conversion from measurement relation to total-pressure loss model.']}
    out=project/'milestones/reproducibility/halton-pra-formula-ocr.json'; out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':report['status'],'recognition':records},ensure_ascii=False,indent=2))
