"""Offline numeric-evidence training; no private records are bundled.

Requires scikit-learn==1.9.1 in a development environment only. Evidence is a list
of {student: one_based_index, details: {zero_based_question: reader_v7_detail}}.
Reviewed records are the same approved-only input as benchmark.py. Supply only
the training students; keep all external validation students out of both files.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from learned_marks import option_features, eligible, scope_hash, FEATURE_VERSION


def train(evidence, reviewed, master, config):
    from sklearn.ensemble import ExtraTreesClassifier
    from sklearn.model_selection import LeaveOneGroupOut
    from processor import raster
    import pymupdf
    rows = json.loads(Path(evidence).read_text())
    refs = json.loads(Path(reviewed).read_text())
    if not refs or any(r['status'] != 'approved' for r in refs):
        raise ValueError('Only approved training records are accepted.')
    labels = {}
    for r in refs:
        data = json.loads(r['data']) if isinstance(r['data'],str) else r['data']
        answers = data['answers']
        if len(answers) != 25 or any(a not in ('A','B','C','D','-') for a in answers):
            raise ValueError('Training decisions must be complete.')
        labels[r['idx']+1] = answers
    features, targets, groups, questions = [], [], [], []
    for row in rows:
        if len(row['details']) != 25:
            raise ValueError('All 25 evidence regions are required per training paper.')
        for q,d in row['details'].items():
            expected = labels[row['student']][int(q)]
            features.extend(option_features(d))
            targets.extend([expected == a for a in 'ABCD'])
            groups.extend([row['student']]*4)
            questions.append((d,expected))
    if len(set(groups)) < 5:
        raise ValueError('At least five independently reviewed students are needed for grouped checks.')
    x,y,groups = np.array(features),np.array(targets),np.array(groups)
    clf = ExtraTreesClassifier(n_estimators=300,max_depth=10,min_samples_leaf=3,
                              max_features=.7,class_weight='balanced',random_state=42,n_jobs=2)
    oof = np.zeros(len(y))
    for fit,check in LeaveOneGroupOut().split(x,y,groups):
        clf.fit(x[fit],y[fit]);oof[check] = clf.predict_proba(x[check])[:,1]
    matches = errors = 0
    for (d,expected),scores in zip(questions,oof.reshape(-1,4)):
        order = np.argsort(scores)
        if eligible(d) and scores[order[-1]] >= .75 and scores[order[-2]] < .15:
            choice = 'ABCD'[order[-1]]
            matches += choice == expected;errors += choice != expected
    if errors:
        raise ValueError(f'Grouped checks found {errors} incorrect recovered answers; model not exported.')
    clf.fit(x,y)
    trees = []
    for estimator in clf.estimators_:
        t = estimator.tree_
        positive = t.value[:,0,1]/t.value[:,0,:].sum(1)
        trees.append(dict(left=t.children_left.tolist(),right=t.children_right.tolist(),
                          feature=t.feature.tolist(),threshold=t.threshold.tolist(),positive=positive.tolist()))
    conf = json.loads(Path(config).read_text())
    with pymupdf.open(master) as doc:
        if len(doc) != 2: raise ValueError('Expected a two-page master.')
        scopes = [scope_hash(conf['mapping'],i,raster(page)) for i,page in enumerate(doc)]
    return dict(id='class10-ink-v1',feature_version=FEATURE_VERSION,reader_base_version=7,
                threshold=.75,secondary_cap=.15,scopes=scopes,training_students=len(set(groups)),
                training_questions=len(questions),automatic_release_validated=False,trees=trees), {
                'grouped_additional_matches':int(matches),'grouped_additional_errors':int(errors),
                'limitation':'Calibration only; separate scans and label review required before release.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('evidence','reviewed','master','config','output'):p.add_argument('--'+key,required=True)
    args = vars(p.parse_args());output = Path(args.pop('output'))
    model,report = train(**args)
    output.write_text(json.dumps(model,separators=(',',':')))
    print(json.dumps(report))
