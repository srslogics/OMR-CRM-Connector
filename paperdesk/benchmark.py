"""Offline benchmark against approved records. Reference answers never enter detection.

Usage: python benchmark.py --master blank.pdf --source scans.pdf --config config.json
       --reviewed approved.json --output report.json
Approved JSON is a list of {idx, status, data} records; keep it outside Git.
"""
import argparse
import json
import time
from pathlib import Path
import pymupdf
from processor import raster, align, detect_page, MARK_READER_VERSION
from review_audit import comparison


def benchmark(master, source, config, reviewed):
    conf = json.loads(Path(config).read_text())
    rows = json.loads(Path(reviewed).read_text())
    if not rows or any(r['status'] != 'approved' for r in rows):
        raise ValueError('Use approved reference records only.')
    with pymupdf.open(master) as pdf:
        if len(pdf) != 2:
            raise ValueError('The master must have two pages.')
        masters = [raster(page) for page in pdf]
    totals = dict(questions=0, matched=0, unresolved=0, different=0, strong=0,
                  strong_different=0, suggestions=0, suggestion_matches=0)
    results = []
    started = time.monotonic()
    with pymupdf.open(source) as pdf:
        if len(pdf) % 2 or len({r['idx'] for r in rows}) != len(rows):
            raise ValueError('Check page pairing and unique reference indices.')
        for row in rows:
            idx = row['idx']
            if idx < 0 or idx * 2 + 1 >= len(pdf):
                raise ValueError('Reference student index is outside the source PDF.')
            detected = [{'answer': '?', 'confidence': 'review', 'reason': 'Page alignment failed.'} for _ in range(25)]
            for page in range(2):
                image, quality = align(raster(pdf[idx * 2 + page]), masters[page])
                if image is not None:
                    for q, value in detect_page(image, masters[page], conf['mapping'], page).items():
                        detected[q] = value
            # Reference decisions are read only after inference finishes.
            data = json.loads(row['data']) if isinstance(row['data'], str) else row['data']
            if len(data['answers']) != 25 or '?' in data['answers']:
                raise ValueError('Reference answers must be fully reviewed.')
            for q, (d, expected) in enumerate(zip(detected, data['answers']), 1):
                actual = d['answer']
                state = 'unresolved' if actual == '?' else 'matched' if actual == expected else 'different'
                totals['questions'] += 1
                totals[state] += 1
                strong = d.get('confidence') == 'strong'
                totals['strong'] += strong
                totals['strong_different'] += strong and actual != expected
                totals['suggestions'] += bool(d.get('suggested_answer'))
                totals['suggestion_matches'] += d.get('suggested_answer') == expected
                results.append(dict(student=idx + 1, question=q, detected=actual, reviewed=expected,
                                    state=state, confidence=d.get('confidence'), reason=d['reason'],
                                    suggestion=d.get('suggested_answer')))
    return dict(reader_version=MARK_READER_VERSION, totals=totals, seconds=round(time.monotonic()-started, 2),
                stored_review_comparison=comparison(rows), answers=results,
                limitation='Calibration set, not independent validation. Student OCR comparison uses stored suggestions, not a fresh OCR run. No records were changed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('master', 'source', 'config', 'reviewed', 'output'):
        parser.add_argument('--'+arg, required=True)
    args = vars(parser.parse_args())
    output = Path(args.pop('output'))
    report = benchmark(**args)
    output.write_text(json.dumps(report, indent=2))
    output.chmod(0o600)
    print(json.dumps({'reader_version': report['reader_version'], **report['totals'], 'seconds': report['seconds']}))
