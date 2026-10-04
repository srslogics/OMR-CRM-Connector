"""Client-facing totals. Original recognition evidence is never rewritten.

Requested policy: eight marks once for unresolved alignment, maximum 100.
This is an administrative adjustment, not a claim that answers were recognised.
"""
import json
from student_details import details_ready

GRACE_MARKS = 8
POLICY = 'Eight marks once for unresolved alignment; total capped at 100.'

def result_row(row):
    data = json.loads(row['data']) if isinstance(row['data'], str) else row['data']
    details = data.get('details', [])
    alignment_uncertain = any(
        answer == '?' and ('align' in str(details[i].get('reason', '')).lower()
                           or 'registration' in str(details[i].get('reason', '')).lower())
        for i, answer in enumerate(data.get('answers', [])) if i < len(details)
    )
    base = max(0, min(100, int(data['score']['total'])))
    grace = min(GRACE_MARKS, 100-base) if alignment_uncertain else 0
    fields = data.get('fields', {})
    return {key: fields.get(key, '') for key in ('name','school','father_mobile','mother_mobile')} | {
        'marks': base+grace, 'grace': grace,
        'details_status': 'Checked' if details_ready(data) else 'Not verified',
        'result_status': 'Approved' if row.get('status') == 'approved' and details_ready(data) else 'Provisional',
    }
