"""CPU-only per-student inference. Child processes do not access the database."""
from pathlib import Path
import cv2
import pymupdf as fitz
from processor import (FIELDS, MARK_READER_VERSION, raster, align, detail_pixels,
                       detect_page_with_retry, score)
from student_details import extract_details, empty_reading


def infer_student(doc, idx, masters, high_masters, conf, folder):
    readings={k:empty_reading('Page alignment failed or field not mapped. Read the original PDF.') for k in FIELDS};fields={k:'' for k in FIELDS};answers=['?']*25;details=[{'reason':'Page alignment needs review','evidence':[]} for _ in range(25)];flags=[]
    for pageno in range(2):
        im=raster(doc[idx*2+pageno]);aligned,quality,transform=align(im,masters[pageno],True)
        if aligned is None:
            flags.append(f'Page {pageno+1}: alignment failed; check page order and scan quality.')
            cv2.imwrite(str(folder/f'{idx}-{pageno}.png'),im);continue
        cv2.imwrite(str(folder/f'{idx}-{pageno}.png'),aligned)
        for q,d in detect_page_with_retry(doc[idx*2+pageno],aligned,masters[pageno],conf['mapping'],pageno,high_masters[pageno]).items():
            answers[q]=d['answer'];details[q]=d
        if pageno==0:
            pixels,reference=detail_pixels(doc[idx*2],im,masters[0],transform)
            readings=extract_details(pixels,reference,conf.get('fields',{}),folder,idx)
            fields={k:readings[k]['suggested'] for k in FIELDS}
            del pixels,reference
    flags.append('Verify student details, both pages and all detected answers before approving.')
    data={'mark_reader_version':MARK_READER_VERSION,'detected_answers':list(answers),'answer_overrides':[],'fields':fields,'field_ocr':readings,'field_review':{},'answers':answers,'details':details,'flags':flags,'pairing_verified':False,'score':score(answers,conf['key'])}
    return data

_context = None

def prepare_worker(source, master, page_paths, conf, folder):
    global _context
    cv2.setNumThreads(1)
    with fitz.open(master) as pdf:
        high_masters = [raster(p, 3.4) for p in pdf]
    masters = [cv2.imread(str(path)) for path in page_paths]
    if any(p is None for p in masters):
        raise ValueError('Master images unavailable')
    _context = (fitz.open(source), masters, high_masters, conf, Path(folder))

def infer_index(idx):
    doc, masters, high_masters, conf, folder = _context
    return idx, infer_student(doc, idx, masters, high_masters, conf, folder)
