"""Smooth residual page-shape correction after validated global registration.

The low-frequency displacement field follows printed structure, rather than
fitting an independent transform to each pen stroke. The original image stays
the evidence of record. This module has no access to keys or student labels.
"""
import cv2
import numpy as np


def refine(image, template, contrast):
    if image.shape != template.shape or min(image.shape[:2]) < 64:
        return None, {'accepted': False, 'reason': 'Mismatched or small page'}
    h, w = template.shape[:2]
    size = (w // 2, h // 2)
    a = cv2.resize(contrast(template), size)
    b = cv2.resize(contrast(image), size)
    if np.count_nonzero(a > 35) < 200:
        return None, {'accepted': False, 'reason': 'Insufficient printed structure'}
    flow = cv2.calcOpticalFlowFarneback(a, b, None, .5, 3, 31, 5, 7, 1.5, 0)
    flow = cv2.GaussianBlur(flow, (0, 0), 12)
    flow = cv2.resize(flow, (w, h)) * 2
    limit = 18 * w / 1100
    displacement = np.linalg.norm(flow, axis=2)
    # Reject unsupported distortions, rather than forcing an arbitrary warp.
    if not np.isfinite(flow).all() or np.percentile(displacement, 99) > limit:
        return None, {'accepted': False, 'reason': 'Residual distortion too large'}
    yy, xx = np.mgrid[:h, :w].astype('float32')
    pixels = cv2.remap(image, xx + flow[:, :, 0], yy + flow[:, :, 1],
                       cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                       borderValue=(255, 255, 255))
    return pixels, {'accepted': True, 'method': 'smooth-local-flow',
                    'p95_displacement': round(float(np.percentile(displacement, 95)), 2)}


def merge_reads(original, refined):
    """Keep known answers, recover supported misses, and abstain on conflicts."""
    result = {}
    for q, before in original.items():
        after = refined.get(q)
        if after is None:
            result[q] = before
            continue
        a, b = before['answer'], after['answer']
        entry = {**before, 'local_read': {'answer': b,
                  'confidence': after.get('confidence'), 'reason': after.get('reason')}}
        if a != '?' and b != '?' and a != b:
            entry.update(answer='?', confidence='review',
                         reason='Original and locally aligned readings disagree.')
        elif a == '?' and b != '?' and after.get('confidence') == 'strong':
            if before.get('suggested_answer') in (None, b):
                entry.update(answer=b, confidence='review',
                             reason='Mark recovered after local page-shape correction.')
        result[q] = entry
    return result
