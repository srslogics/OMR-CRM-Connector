"""Template-scoped learned mark recovery. Forest scores are not probabilities.

Only numeric stroke/ink evidence enters the model: no names, printed question
text, question numbers, student IDs, answer keys or reviewed answers.
"""
import hashlib
import json
import logging
from functools import lru_cache
from pathlib import Path
import numpy as np

FEATURE_VERSION = 1
MODEL_PATH = Path(__file__).parent / 'assets' / 'class10-mark-model-v1.json'

def option_features(d):
 arrays=[]
 for r,factor in [(d,1),(d.get('second_resolution',{}),4)]:
  values=[]
  for i in range(4):
   ls=r.get('evidence',[]);e=ls[i] if i<len(ls) and ls[i] else {}
   ls=r.get('checkbox_evidence',[]);b=ls[i] if i<len(ls) and ls[i] else {}
   ls=r.get('option_evidence',[]);o=ls[i] if i<len(ls) and ls[i] else {}
   values.append([e.get('ratio',0),e.get('pixels',0)/factor,e.get('inside_pixels',0)/factor,e.get('box_found',False),*([v/factor for v in b.get('pixels_by_threshold',[0]*3)]),b.get('registration_cost',2),*([abs(v)/factor**.5 for v in b.get('shift',[0,0])]),*([v/factor for v in o.get('v',[0]*3)]),o.get('cost',2)])
  arrays.append(np.array(values,float))
 colors=d.get('whole_option_color',[[0]*3]*4);arrays.append(np.array(colors,float))
 strokes=[]
 for i in range(4):
  votes=[]
  for j,r in enumerate(d.get('stroke_reads',[])[:3]):
   a=[m for m in r.get('marks',[]) if m['option']==i];factor=2 if j==2 else 1
   votes.extend([sum(m['long'] for m in a),max([m['width']/factor for m in a],default=0),max([m['height']/factor for m in a],default=0)])
  strokes.append(votes+[0]*(9-len(votes)))
 arrays.append(np.array(strokes,float));raw=np.concatenate(arrays,axis=1)
 return np.concatenate([raw,raw/(raw.max(0)+1),raw-np.partition(raw,2,axis=0)[2]],axis=1)

def eligible(detail):
    reason = detail.get('reason', '').lower()
    return detail.get('answer') == '?' and not any(word in reason for word in (
        'no reliable mark', 'separate checkmark', 'readings disagree',
        'readers disagree', 'marks disagree', 'multiple marks or correction'))


def scope_hash(mapping, page, template):
    geometry = json.dumps(mapping, sort_keys=True, separators=(',', ':')).encode()
    digest = hashlib.sha256(geometry + str(page).encode())
    digest.update(str(template.shape).encode())
    digest.update(template.tobytes())
    return digest.hexdigest()


@lru_cache(maxsize=1)
def load_model():
    model = json.loads(MODEL_PATH.read_text())
    if model['feature_version'] != FEATURE_VERSION or model['reader_base_version'] != 7:
        raise ValueError('Unsupported mark model')
    # Numeric arrays only: never unpickle a model in production.
    trees = []
    for t in model['trees']:
        trees.append({k: np.asarray(v, dtype=np.int32 if k in ('left','right','feature') else np.float64)
                      for k,v in t.items()})
    return model, trees


def predict(features, trees):
    # scikit-learn evaluates tree inputs as float32; match it exactly.
    values = np.asarray(features, dtype=np.float32)
    if values.shape != (4, 120) or not np.isfinite(values).all():
        raise ValueError('Invalid mark evidence')
    scores = np.zeros(4)
    for tree in trees:
        nodes = np.zeros(4, dtype=np.int32)
        for _ in range(12):
            active = tree['left'][nodes] != -1
            if not active.any(): break
            rows = np.where(active)[0]
            current = nodes[rows]
            left = values[rows, tree['feature'][current]] <= tree['threshold'][current]
            nodes[rows] = np.where(left, tree['left'][current], tree['right'][current])
        if np.any(tree['left'][nodes] != -1):
            raise ValueError('Invalid mark model depth')
        scores += tree['positive'][nodes]
    return scores / len(trees)


def recover_page(readings, mapping, page, template):
    try:
        model, trees = load_model()
        if scope_hash(mapping, page, template) not in model['scopes']:
            return readings
        recovered = {}
        for q, d in readings.items():
            recovered[q] = d
            if not eligible(d) or not d.get('local_registration',{}).get('accepted'):
                continue
            if not all(key in d for key in ('second_resolution','whole_option_color','stroke_reads')):
                continue
            scores = predict(option_features(d), trees)
            order = np.argsort(scores)
            audit = {'model':model['id'], 'scores':scores.round(5).tolist(),
                     'basis':'Learned ink evidence; scores are not calibrated accuracy.'}
            recovered[q] = {**d, 'learned_reader':audit}
            if scores[order[-1]] >= model['threshold'] and scores[order[-2]] < model['secondary_cap']:
                choice = 'ABCD'[order[-1]]
                alternatives = [d.get('suggested_answer'),
                                d['second_resolution'].get('answer'),
                                d.get('local_read',{}).get('answer')]
                if any(a in ('A','B','C','D') and a != choice for a in alternatives):
                    continue
                recovered[q].update(answer=choice, confidence='review',
                    reason='Mark recovered by the template-specific classifier; retained for verification.')
        return recovered
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        logging.warning('Learned mark reader unavailable; original evidence retained.')
        return readings
