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

## Database latency update — 2026-09-29

Reused 2–4 PostgreSQL connections, single-query session lookup, autocommit reads, one-query cached-file validation/retrieval, batched dashboard counts and compact batch summaries. Writes remain transactional. Polling is limited to one outstanding progress request, skips hidden tabs and ignores responses after navigation.

Five sequential read-only comparisons from the development machine to the configured Supabase session pooler: previous two-connection account lookup median 688 ms; warmed pooled single-query lookup median 27 ms. These measure database work, not live Render HTTP latency or OCR throughput. No production records were modified for this benchmark.

Passed: four local integration tests; four integration tests against an isolated PostgreSQL test schema; persistence/pool reuse/cache replacement/rollback check; setup-dialog regression checks; overlapping polling/navigation/hidden-tab/completion checks. Scan routes continue checking authentication; no public scan cache was introduced. Render cold starts are unaffected.

## Faint-mark reader (2026-09-29)

- Local brightness normalization and printed-ink registration replace the fixed darkness cutoff. Interior checkbox evidence separates tick tails from answer selections. The official answer key is never provided to detection.
- Unreadable, missing, off-box, conflicting or poorly aligned marks produce `?`, not an automatically scored blank. Staff may still confirm a blank or a genuine zero. Unapproved zero totals are displayed as pending review; other draft totals are labelled incomplete when necessary.
- Added authenticated original/contrast answer crops and batch rereading. Approved papers are skipped; manual answer changes (including legacy audit history), student fields and field confirmations are preserved. Version comparisons prevent overwriting concurrent reviews. Rereads are audited.
- Synthetic tests cover faint grey ink above the old darkness threshold, uneven lighting, translation, two marks, missing evidence, genuine zero scoring, manual correction preservation, approval protection and authenticated evidence access. This is not a claim of fully automated accuracy on handwritten papers.
- The private 20-page pilot was inspected separately, including both prior zero-score papers. No real student scans or identities are included in repository fixtures. Some students tick beside printed answer labels instead of checkboxes; these still require review in the full scan.

## Evidence checks and exception-first review (2026-09-30)

Reader v3 adds independently aligned checkbox interiors at three contrast thresholds. A strong-evidence label requires a stable selected option, readable competing boxes, no competing faint mark, bounded registration, and no disagreement with the existing reader. This label is an evidence rule, **not a calibrated probability** or automatic approval. Missing boxes, option-label ticks and disagreement remain exceptions.

Private pilot benchmark: 118/250 answer regions met the strong rule. Of 75 reference answers across three papers (one existing staff-approved paper and two visually transcribed papers), 39 met the strong rule; all 39 matched. This is a small, partly development-used, single-template sample, not independent multi-class validation. It does not establish a production error rate or justify unattended release of all 2,610 papers. Real scans/reference labels remain outside Git. Re-run on separately labelled classes and scan sources before scaling.

Review defaults to answer exceptions; all choices remain inspectable. Individual confirmations are saved and protected during rereading. Editing an answer invalidates its check. A next-exception action saves the draft and navigates across papers without approving results or changing the separate student-detail checks. Approved papers remain unchanged.

Passed 12 local unit/integration tests, plus UI tests for exception filtering, stale confirmations, zero/partial score display, polling and exam setup. Synthetic tests include faint marks, shadows, translations, competing marks, missing competing boxes, persistence of confirmations and approved-result protection.
