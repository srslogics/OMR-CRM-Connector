# Validation record

Verified locally on 26 September 2026 with Python 3.13 and CPU ONNX Runtime. No real student records or scans are committed to this repository.

## Student details: private Class 10 calibration sample

Ten consecutive student pairs (20 pages) from a supplied combined PDF were processed locally. All eight header fields were mapped against the supplied blank Class 10 master. The reference transcription was visually read from the scan crops; uncertain, incomplete or overwritten values were excluded rather than inferred from other students or the exam class.

Of 80 possible fields, 65 were clearly readable and filled, three were blank and 12 were ambiguous/incomplete. Exact comparison ignores letter case and whitespace only; it does not accept similar names or approximate phone digits.

| Field | Readable filled references | Previous reader: exact | Updated reader: exact |
|---|---:|---:|---:|
| Student name | 9 | 0 | 4 |
| School | 10 | 0 | 2 |
| Class | 9 | 0 | 6 |
| Section | 9 | 0 | 8 |
| Taluka | 7 | 1 | 3 |
| District | 10 | 1 | 6 |
| Father's mobile | 6 | 0 | 6 |
| Mother's mobile | 5 | 0 | 5 |
| **Total** | **65** | **2** | **40** |

All three reference blank fields had empty suggestions with a prompt to check whether they were blank or unreadable. The 12 excluded fields still require manual review. Eleven readable phone numbers matched exactly; nine other phone fields were excluded as ambiguous or incomplete. This does **not** establish 100% phone-number accuracy.

The same 10 papers were used while developing the preprocessing and ranking: this is a calibration result, not a held-out accuracy benchmark. No inference-only method is accurate enough here to release student records without checking the source. Additional classes, schools, handwriting styles and a second reviewer are needed for acceptance testing. English/Latin handwriting only; Marathi handwriting remains unvalidated. No reference correction was fed into OCR at runtime, and there is no student/school lookup dictionary.

Detail extraction, registration and writing crops took approximately 7 seconds for these 10 papers on the local development machine. The complete application pipeline, including all 20 pages and answer processing, took approximately 9 seconds and generated 80 field crops. This excludes uploads and staff review and is **not** a Render Free performance guarantee. All 10 records remained in review; no real student result or identity was automatically approved. There were still 64 unresolved answer detections, unchanged from the earlier pilot.

## Automated and browser checks

- Four automated test methods cover the generated three-student workflow and a generated 15-student boundary batch. Expected synthetic scores remain 100, 76, and 92 provisional, including a blank and an unresolved double mark. A 16-student upload is rejected.
- Student details can be exported with unresolved answers only after every field has a recorded decision, a name is confirmed and page pairing is checked. Results exports still require result approval.
- Incomplete phone numbers cannot be marked confirmed through the API. Editing a confirmed value resets its confirmation. Confirmed blank/unreadable values must be empty and export their explicit statuses.
- Rereading details preserves saved manual corrections and rejects stale versions. Older approvals without field checks are excluded from results exports and marksheets until checked.
- Authentication, protected field crops and downloads, same-origin writes, immutable keys, odd-page rejection, audit records, formula escaping and concurrent-edit protection are exercised.
- A headless Chrome browser check used synthetic records: eight field cards, crop enlargement, confirmation reset after editing, saving, details-only Excel download before marks approval, desktop (1440 px) and mobile (390 px). No script errors or mobile page overflow were found. Screenshots were inspected locally.

The MVP limit remains 15 students (30 pages) per batch; start with 10. No live Render deployment or performance claim follows from these local checks.
