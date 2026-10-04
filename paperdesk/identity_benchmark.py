"""Exact identity-field evaluation; private references stay outside the repo.

JSON inputs: [{"student":"opaque-local-id", "field":"name", "text":"..."}].
References may use null text to exclude ambiguous handwriting. Empty text means
confirmed blank. Predictions never receive reference text during recognition.
"""
import argparse,json,re
from collections import Counter
FIELDS=('name','school','father_mobile','mother_mobile')

def index(rows,reference=False):
    result={}
    for row in rows:
        key=(str(row['student']),row['field'])
        if key[1] not in FIELDS:raise ValueError('Unsupported identity field')
        if key in result:raise ValueError('Duplicate student/field entry')
        value=row['text']
        if value is not None and not isinstance(value,str):raise ValueError('Text must be a string; never parse phones as numbers')
        if value is None and not reference:raise ValueError('Prediction text must be a string')
        result[key]=value
    return result

def normalise(value,field):
    if 'mobile' in field:
        # Formatting is ignored; no digit, prefix or OCR-letter correction.
        return re.sub(r'[\s()\-]','',value)
    return ''.join(value.casefold().split())

def evaluate(references,predictions):
    truth=index(references,True);actual=index(predictions)
    if set(actual)-set(truth):raise ValueError('Prediction has no matching reference')
    report={field:Counter() for field in FIELDS}
    for (student,field),expected in truth.items():
        stats=report[field]
        if expected is None:stats['excluded_ambiguous']+=1;continue
        predicted=actual.get((student,field),'');stats['evaluated']+=1
        stats['missing_prediction']+=(student,field) not in actual
        match=normalise(predicted,field)==normalise(expected,field)
        stats['exact']+=match
        if expected:
            stats['filled']+=1;stats['filled_exact']+=match
            stats['wrong_nonempty']+=bool(predicted) and not match
            stats['missed_filled']+=not predicted
        else:
            stats['blank']+=1;stats['blank_exact']+=not predicted
            stats['false_text_on_blank']+=bool(predicted)
    return {field:{**counts,'exact_rate':round(counts['exact']/counts['evaluated'],4) if counts['evaluated'] else None,
                   'filled_exact_rate':round(counts['filled_exact']/counts['filled'],4) if counts['filled'] else None}
            for field,counts in report.items()}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--references',required=True);parser.add_argument('--predictions',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    with open(args.references) as f:refs=json.load(f)
    with open(args.predictions) as f:preds=json.load(f)
    report=evaluate(refs,preds)
    with open(args.output,'w') as f:json.dump(report,f,indent=2)
    print(json.dumps(report,indent=2))
