"""Processing-team workload, without changing client-reviewed records."""
import json
from processor import FIELDS
from student_details import details_ready


def pending_items(row):
    data = json.loads(row['data']) if isinstance(row['data'], str) else row['data']
    if row['status'] == 'approved' and details_ready(data):
        return None
    checks = data.get('answer_checks', {})
    details = data.get('details', [])
    answers = []
    for i, answer in enumerate(data['answers']):
        detail = details[i] if i < len(details) else {}
        confirmed = answer != '?' and checks.get(str(i)) == answer
        strong = answer != '?' and detail.get('answer') == answer and detail.get('confidence') == 'strong'
        if not (confirmed or strong):
            answers.append(i + 1)
    fields = [key for key in FIELDS if
              data.get('field_review', {}).get(key, {}).get('status') not in ('verified', 'blank', 'unreadable')
              or data.get('field_review', {}).get(key, {}).get('value') != data.get('fields', {}).get(key)]
    start_page = row.get('start_page') or 0
    return {'id': row['id'], 'batch_id': row['batch_id'], 'batch_name': row['batch_name'],
            'exam_name': row['exam_name'], 'student': start_page // 2 + row['idx'] + 1,
            'source_pages': [start_page + row['idx'] * 2 + 1, start_page + row['idx'] * 2 + 2],
            'answers': answers, 'fields': fields, 'pairing_required': not data.get('pairing_verified'),
            'ready_for_approval': not answers and details_ready(data)}
