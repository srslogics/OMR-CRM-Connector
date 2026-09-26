"""Local OCR suggestions and explicit, value-bound student-detail verification.

Recognition scores rank suggestions; they are NOT probabilities of a correct
identity. Never auto-confirm a field, complete a phone number or infer a name.
"""
from pathlib import Path
import logging
import re
import threading
import cv2
import numpy as np
from processor import FIELDS, crop, ocr_crop
from setup_ocr import MODEL

_engine = None
_engine_lock = threading.Lock()
PHONE_FIELDS = {'father_mobile', 'mother_mobile'}
REVIEW_STATES = {'pending', 'verified', 'blank', 'unreadable'}

def recognizer():
    global _engine
    if not MODEL.exists():
        return None
    with _engine_lock:
        if _engine is None:
            import onnxruntime as ort
            ort.disable_telemetry_events()
            options = ort.SessionOptions()
            options.intra_op_num_threads = 2
            options.inter_op_num_threads = 1
            session = ort.InferenceSession(str(MODEL), sess_options=options, providers=['CPUExecutionProvider'])
            chars = [''] + session.get_modelmeta().custom_metadata_map['character'].splitlines() + [' ']
            _engine = session, chars
    return _engine

def read_line(image):
    engine = recognizer()
    if engine is None or not image.size:
        return '', 0.0
    session, chars = engine
    h, w = image.shape[:2]
    # Bounding the width limits memory for accidentally oversized mapped areas.
    width = min(2048, max(16, round(48 * w / h)))
    tensor = cv2.resize(image, (width, 48)).astype('float32') / 127.5 - 1
    prediction = session.run(None, {'x': tensor.transpose(2, 0, 1)[None]})[0][0]
    ids = prediction.argmax(1)
    selected = (ids != 0) & (ids != np.r_[-1, ids[:-1]])
    text = ''.join(chars[i] for i in ids[selected]).strip()
    confidence = float(prediction.max(1)[selected].mean()) if selected.any() else 0.0
    return text, round(confidence, 3)

def evidence_rect(box, shape):
    """Small vertical margin retains ascenders/descenders near printed borders."""
    x, y, w, h = box
    pad = min(h * .20, .004)
    top = max(0, y - pad)
    return [x, top, w, min(1, y + h + pad) - top]

def clean_grid(image):
    grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    grey = cv2.normalize(grey, None, 0, 255, cv2.NORM_MINMAX)
    ink = cv2.adaptiveThreshold(grey, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 12)
    h = grey.shape[0]
    vertical = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((max(13, round(h * .6)), 1), np.uint8))
    horizontal = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((1, max(30, round(h * 1.3))), np.uint8))
    mask = cv2.dilate(vertical | horizontal, np.ones((2, 2), np.uint8))
    grey[mask > 0] = 255
    return cv2.cvtColor(grey, cv2.COLOR_GRAY2BGR)

def grid_interiors(image, template):
    """Read cell interiors using dividers from the blank, never from pen strokes."""
    h, w = image.shape[:2]
    grey = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    ink = cv2.threshold(grey, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    vertical = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((max(8, round(h * .5)), 1), np.uint8))
    indices = np.where(np.mean(vertical > 0, axis=0) > .45)[0]
    groups = np.split(indices, np.where(np.diff(indices) > 1)[0] + 1)
    positions = [int(group.mean()) for group in groups if group.size]
    if len(positions) < 3:
        return None
    step = float(np.median(np.diff(positions)))
    if step < 5 or step > h * 2:
        return None
    positions = sorted(set([0] + positions + [w - 1]))
    positions = [x for i, x in enumerate(positions) if i == 0 or x - positions[i - 1] > step * .35]
    tiles = []
    for left, right in zip(positions, positions[1:]):
        if right - left < step * .5:
            continue
        margin = max(2, round(step * .1))
        part = image[:, left + margin:right - margin]
        if not part.size:
            continue
        reference = grey[:, left + margin:right - margin]
        rows = np.mean(reference < 170, axis=1)
        top = np.where(rows[:int(h * .35)] > .45)[0]
        bottom = np.where(rows[int(h * .65):] > .45)[0] + int(h * .65)
        lo = int(top[-1]) + 2 if top.size else int(h * .1)
        hi = int(bottom[0]) - 1 if bottom.size else int(h * .9)
        if hi - lo < h * .3:
            return None
        part = cv2.resize(part[lo:hi], (part.shape[1], 40))
        tiles.append(cv2.copyMakeBorder(part, 4, 4, 1, 1, cv2.BORDER_CONSTANT, value=(255, 255, 255)))
    return cv2.hconcat(tiles) if tiles else None

def normalise(value, key):
    value = ' '.join(str(value).split())
    # Only remove formatting. Do not turn ambiguous letters into digits.
    if key in PHONE_FIELDS:
        return re.sub(r'[\s()\-]', '', value)
    return value

def empty_reading(reason='This field is not mapped. Read it from the original PDF.'):
    return {'suggested': '', 'candidates': [], 'state': 'unavailable', 'reason': reason, 'engine': 'none'}

def extract_field(image, template, box, key, directory, prefix):
    rect = evidence_rect(box, image.shape)
    cut = crop(image, rect)
    blank = crop(template, rect)
    if not cut.size or cut.shape[0] < 3:
        return empty_reading('The mapped area is empty. Read the original PDF.')
    cv2.imwrite(str(Path(directory) / f'{prefix}-field-{key}.png'), cut)
    # Recognition height is fixed; upscale tiny crops before grid suppression.
    scale = max(1, 64 / cut.shape[0])
    resized = cv2.resize(cut, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    reference = cv2.resize(blank, (resized.shape[1], resized.shape[0]))
    candidates = []
    engine_name = 'PP-OCRv5 English (local)'
    try:
        if recognizer() is None:
            engine_name = 'Legacy local OCR'
            value = ocr_crop(image, rect, directory, key)
            if value:
                candidates.append({'text': normalise(value, key), 'score': 0, 'method': 'original'})
        else:
            variants = [('original', resized), ('grid removed', clean_grid(resized))]
            interiors = grid_interiors(resized, reference)
            if interiors is not None:
                variants.append(('cell interiors', interiors))
            for method, variant in variants:
                padded = cv2.copyMakeBorder(variant, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=(255, 255, 255))
                value, confidence = read_line(padded)
                value = normalise(value, key)
                if value:
                    candidates.append({'text': value[:180], 'score': confidence, 'method': method})
    except Exception as error:
        logging.warning('Student OCR unavailable (%s); field requires manual entry.', type(error).__name__)
        return empty_reading('Recognition failed. Enter the value from the scan.')
    # Prefer a structurally complete phone suggestion, never complete its digits.
    # Line removal/cell slicing can erase genuine strokes. Prefer the original
    # when scores are close; retain every alternative for the reviewer.
    def rank(candidate):
        adjustment = 0 if key in PHONE_FIELDS or candidate['method'] == 'original' else .04 if candidate['method'] == 'grid removed' else .06
        complete = key in PHONE_FIELDS and bool(re.fullmatch(r'[0-9]{10}', candidate['text']))
        if key == 'class':
            complete = bool(re.fullmatch(r'[0-9]{1,2}(?:\s*[A-Za-z])?', candidate['text']))
        return (complete, candidate['score'] - adjustment)
    candidates.sort(key=rank, reverse=True)
    unique = []
    for candidate in candidates:
        if candidate['text'].casefold().replace(' ', '') not in {x['text'].casefold().replace(' ', '') for x in unique}:
            unique.append(candidate)
    chosen = unique[0]['text'] if unique else ''
    grey = cv2.cvtColor(cut, cv2.COLOR_BGR2GRAY)
    old = cv2.cvtColor(blank, cv2.COLOR_BGR2GRAY)
    thickness = max(3, round(cut.shape[0] / 14)) | 1
    printed = cv2.dilate((old < 175).astype('uint8'), np.ones((thickness, thickness), np.uint8))
    added_ink = float(((grey < 155) & (printed == 0)).mean())
    if added_ink < .006:
        chosen = ''
    state = 'review'
    reason = 'Compare with the scan and confirm. Recognition scores do not verify identity.'
    if not chosen:
        state, reason = 'unreadable', 'No reliable text found. Check whether this field is blank or unreadable.'
    elif key in PHONE_FIELDS and not re.fullmatch(r'[0-9]{10}', chosen):
        state, reason = 'incomplete', 'Not a complete 10-digit number. Read the scan; do not guess missing digits.'
    elif len(unique) > 1:
        state, reason = 'conflict', 'The reading methods disagree. Compare the alternatives with the original.'
    return {'suggested': chosen, 'candidates': unique, 'state': state, 'reason': reason, 'engine': engine_name}

def extract_details(image, template, mapping, directory, prefix):
    readings = {key: empty_reading() for key in FIELDS}
    for key, region in mapping.items():
        if key in FIELDS and region.get('page') == 0:
            readings[key] = extract_field(image, template, region['box'], key, directory, prefix)
    return readings

def normalise_reviews(incoming, fields):
    """A confirmation is bound to its exact saved value, not just a checkbox."""
    if not isinstance(incoming, dict):
        raise ValueError('Invalid student detail confirmations.')
    result = {}
    for key in FIELDS:
        value = fields.get(key, '')
        item = incoming.get(key, {})
        if not isinstance(item, dict) or item.get('status', 'pending') not in REVIEW_STATES:
            raise ValueError('Invalid student detail confirmation.')
        state = item.get('status', 'pending')
        if item.get('value', '') != value:
            state = 'pending'
        if state == 'verified':
            if not value:
                raise ValueError('Use “Blank on paper” or “Unreadable” for an empty field.')
            if key in PHONE_FIELDS and not re.fullmatch(r'[0-9]{10}', value):
                raise ValueError('A verified mobile number must have exactly 10 digits. Mark unreadable if it cannot be read.')
        if state in {'blank', 'unreadable'} and value:
            raise ValueError('Blank or unreadable fields must have an empty value.')
        result[key] = {'status': state, 'value': value}
    return result

def details_ready(data):
    if not data.get('pairing_verified') or not data.get('fields', {}).get('name'):
        return False
    reviews = data.get('field_review', {})
    for key in FIELDS:
        item = reviews.get(key, {})
        if item.get('status') not in {'verified', 'blank', 'unreadable'} or item.get('value') != data['fields'].get(key, ''):
            return False
    return reviews.get('name', {}).get('status') == 'verified'
