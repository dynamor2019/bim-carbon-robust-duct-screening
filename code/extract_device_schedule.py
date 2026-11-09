"""Extract local device-schedule pages for evidence; do not impute blank cells."""
import hashlib
import json
from pathlib import Path
import fitz


def main():
    project = Path(__file__).resolve().parents[1]
    source = project.parent / 'extracted/HVAC/Device-Schedule/Office_concrete_HVAC_Device Schedule_20240611.pdf'
    target = project / '.dsh-state/source-extracts'
    target.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(source)
    evidence = []
    for n in range(28, 35):
        text = doc[n - 1].get_text('text', sort=True)
        # Preserve both reading order and spatial locations for later visual review.
        text_path = target / f'office_schedule_page{n}.txt'
        text_path.write_text(text, encoding='utf-8', newline='')
        words_path = target / f'office_schedule_page{n}_words.json'
        words_path.write_text(json.dumps(doc[n-1].get_text('words'), ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='')
        evidence.append({'physical_page': n, 'text_path': str(text_path),
                         'text_sha256': hashlib.sha256(text_path.read_bytes()).hexdigest(),
                         'word_boxes_path': str(words_path)})
    doc.close()
    manifest = {'source': str(source), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'pymupdf': fitz.VersionBind, 'pages': evidence,
                'limitation': 'Text/word boxes do not substitute for final visual table verification; blank values are not zero.'}
    output = project / 'milestones/reproducibility/boundary-evidence'
    output.mkdir(parents=True, exist_ok=True)
    (output / 'schedule-extraction.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='')
    print('Extracted existing PDF pages 28–34; source retained unchanged.')


if __name__ == '__main__':
    main()
