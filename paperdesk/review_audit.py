"""Compare stored machine evidence with approved decisions; never train on keys."""
from collections import Counter
import json
from processor import FIELDS


def comparison(rows):
    answers = Counter(total=0, matched=0, unresolved=0, different=0, unavailable=0)
    fields = {k: dict(readable=0, matched=0, different=0, blank_or_unreadable=0) for k in FIELDS}
    questions = {str(i): dict(matched=0, unresolved=0, different=0) for i in range(1, 26)}
    approved = 0
    students = []
    reasons = Counter()
    for row in rows:
        row = dict(row)
        if row['status'] != 'approved':
            continue
        approved += 1
        data = json.loads(row['data']) if isinstance(row['data'], str) else row['data']
        student = {'student': row.get('idx', approved - 1) + 1, 'answers': [], 'fields': []}
        detected = data.get('detected_answers')
        if not isinstance(detected, list) or len(detected) != 25:
            answers['unavailable'] += 25
        else:
            for i, (before, final) in enumerate(zip(detected, data['answers'])):
                state = 'unresolved' if before == '?' else 'matched' if before == final else 'different'
                answers['total'] += 1
                answers[state] += 1
                questions[str(i + 1)][state] += 1
                if state != 'matched':
                    detail = (data.get('details') or [])
                    reason = detail[i].get('reason', 'Reason unavailable') if i < len(detail) else 'Reason unavailable'
                    reasons[reason] += 1
                    student['answers'].append({'question': i + 1, 'machine': before,
                                               'reviewed': final, 'state': state, 'reason': reason})
        for key in FIELDS:
            review = data.get('field_review', {}).get(key, {})
            if review.get('value') != data.get('fields', {}).get(key):
                continue
            if review.get('status') in ('blank', 'unreadable'):
                fields[key]['blank_or_unreadable'] += 1
            elif review.get('status') == 'verified':
                fields[key]['readable'] += 1
                norm = lambda value: ''.join(str(value).casefold().split())
                suggestion = data.get('field_ocr', {}).get(key, {}).get('suggested', '')
                state = 'matched' if norm(suggestion) == norm(review['value']) else 'different'
                fields[key][state] += 1
                if state == 'different':
                    student['fields'].append(key)
        students.append(student)
    return {'approved_students': approved, 'answers': dict(answers), 'fields': fields,
            'students': students, 'failure_reasons': dict(reasons),
            'questions': questions, 'basis': 'Saved machine readings compared with client-approved entries. Missing historical readings are excluded. This is not a new scan run or an independent accuracy test.'}
