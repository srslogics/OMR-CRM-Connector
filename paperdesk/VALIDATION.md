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

## Client-reviewed comparison — 2026-10-02

All ten pilot papers are approved by the client. Their stored decisions are now
used as calibration references, without changing any approved record. A fresh
v3 rerun on the original master/source matched 145/250 decisions, abstained on
104 and differed on one (student 3, Q21). This fresh rerun differs from older
published counts; use the reproducible benchmark and its exact inputs.

Reader v4 checks adjacent option text and faint checkbox outlines. Weak checkbox
reads with competing option ink become unresolved. Recovered faint boxes remain
reviewable. Text-side choices are **suggestions only**: they remain `?` and cannot
enter final results until a person selects and approves them. Strong checkbox
reads retain their existing separate interior-evidence requirements.

The same calibration set now has 151 matches, 99 unresolved and zero differing
selected answers. 108 readings have strong checkbox evidence; all match this
reference set. Fifteen additional text-side suggestions include 13 matches and
two disagreements, demonstrating why suggestions must not be auto-scored. This
is NOT 100% accuracy: unresolved answers are 39.6% of all answers, and this is a
development set rather than an independent holdout.

Saved student OCR suggestions match 45 of 75 client-confirmed readable fields
(after case/whitespace normalization). Five fields are confirmed blank or
unreadable and excluded from that denominator. OCR has not been retrained or
validated for automatic identity release. The audit screen reports these field
misses explicitly. Original machine history missing from a record is reported as
unavailable, never assumed correct.

`benchmark.py --master ... --source ... --config ... --reviewed ... --output ...`
re-runs detection before comparing reference answers, writes an aggregate and
question-level report, and never modifies production records. Keep reviewed
JSON and reports outside Git. No private scans or student identities are shipped
in fixtures. `Review accuracy` in each batch compares saved machine readings to
approved decisions; it does not silently reprocess approved papers.

Bulk release remains blocked by insufficient validation, not by a promise of
perfection. Keep the existing 15-student batch limit. Independently review new
papers from each class and scan source, measure strong-read errors and unresolved
rates separately, and load-test persistent resumable processing before raising
limits. The original two-page pairing assumption must be validated for each
source; missing/reordered pages cannot be inferred from this ten-student sample.

## Higher-resolution retry and detailed audit — 2026-10-02

Reader v5 retries pages containing exceptions at twice the rendering resolution.
The second page registration must independently succeed. A disagreement between
selected answers becomes unresolved. Recovery requires strong checkbox evidence
and no conflicting text-side suggestion; recovered answers remain reviewable.
The key and client reference values never enter inference. Both normal processing
and unapproved-paper rereads use the same retry path as the offline benchmark.

The ten-paper calibration benchmark gives **159 matched, 91 unresolved, zero
different selections out of 250** (v4: 151, 99, zero). Eight additional matches
were recovered. The 108 strong primary readings are unchanged. Runtime was 9.42
seconds locally for mark inference; this excludes OCR, upload, database writes
and staff review and does not predict Render Free throughput. This is still a
calibration set, not a holdout or a basis for automatic release.

The review audit now includes per-student question differences, recorded failure
reasons and names of fields needing correction. It compares historical stored
readings, explicitly distinguished from a fresh v5 rerun. Missing machine
history for the first approved paper remains reported as unavailable. No client
names, phone values or scans are committed to Git.

A trial of tighter per-field registration recovered only 37/75 verified fields,
versus 45/75 saved suggestions. That experiment was rejected; student OCR is
unchanged. Of 30 historical field misses, only four had the correct value among
existing alternatives. Better handwriting recognition and independent examples
remain necessary. Do not relabel these fields as confident.

Passed 20 unit/integration tests, JavaScript syntax validation and four UI
regression suites. Tests cover resolution disagreement, weak retry rejection,
text/checkbox conflict, reviewed-value preservation, approval protection,
SQLite-compatible audit rows and per-student correction counts. The 15-student
limit and approval requirements remain unchanged. Approved pilot records were
not rewritten.

## Bulk intake and interruption recovery — 2026-10-02

Implemented atomic intake into parts of 15 students, duplicate-PDF protection,
page-count bounds, explicit pairing confirmation, queued-work storage estimates
and cleanup of files from failed transactions. Existing approvals are untouched.
The old small-batch API remains supported; the upload UI uses the new bulk API.

Passed five intake tests and one authenticated API/recovery test, alongside the
20 existing Python tests and four JavaScript regression suites. An isolated
PostgreSQL schema verified file persistence, split records and duplicate reuse.
A generated 5,220-page file was split into 174 parts for 2,610 students; every
page number was checked in order. Split plus order verification took 0.96 seconds
locally. These are simple generated pages, NOT scanned-paper OCR throughput.
The recovery test stopped processing after one saved synthetic student, resumed,
and confirmed that the completed record was byte-for-byte unchanged.

A trial of question-local affine registration found two additional strong reads
but also a differing weak read. It was not shipped: the small calibration set
does not justify additional complexity or treating weak alternatives as facts.
Answer/identity accuracy remains as documented for v5. Bulk queue readiness is
not a claim of unattended grading or identity accuracy. The processing team must
handle uncertain readings. The full private archive was not uploaded or processed
as part of these tests.

## Internal processing desk — 2026-10-03

Added an authenticated, paginated team queue across batches; it lists answer
exceptions, unresolved identity fields, page pairing, failed jobs and estimated
storage headroom. Bulk-part source page offsets remain visible. Drafts can be
saved back to the queue without releasing results. This uses the existing
administrator access model; it does not introduce a separate client/staff role.
Strong scan evidence is labelled as unflagged, not as a human confirmation.

Expanded answer evidence images to include option text to the left of checkboxes.
The previous box-only view could hide off-box ticks. The full page remains the
source of truth; the context crop is based on the existing two-column layout.

Processed the next nine Class 10 students (original pages 21–38 of the pilot's
source file), outside the ten-paper calibration set. All 18 pages registered;
printed Class 10 banners were visually checked. There were 83 unresolved answers
out of 225. These are not client-labelled reference papers: no accuracy claim,
final scores or approvals follow from this run. Local marks plus field extraction
took 13.18 seconds; this excludes service/database costs.

Passed 24 unit/integration checks, the authenticated bulk/restart/operations test,
five bulk intake checks and four JavaScript regression suites. Browser QA with
synthetic papers verified queue navigation, expanded scan context and save-and-
return without approval. Production-approved papers were not changed.

The source archive is about 596 MiB. The default hosted document budget remains
180 MiB; it cannot hold the archive. The queue's capacity panel makes this
constraint visible. Do not label the complete archive ready for hosted intake
without providing sufficient durable private storage.

## Bounded parallel processing and option-row reader — 2026-10-03

The web app can now run without the OCR coordinator. A dedicated worker uses
1–4 CPU processes with at most that many students in flight and transactional
per-student checkpoints. Spawned children do not open database connections.
A real spawned-process synthetic test verified sequential/parallel output parity,
interruption with exactly two in-flight students, resume, and preservation of an
existing approved record. Local queue coordinators now share a filesystem lock.

Reader v6 adds a supplementary blue-pen detector across option rows, suppresses
coloured master print and rejects competing grayscale marks or reader conflicts.
It does not guess from the official key and does not automatically approve a
student. On the ten approved calibration papers: 164/250 matched, 86 unresolved,
0 different; 108 primary strong reads matched. This is five additional resolved
answers over v5. Calibration results are not independent accuracy estimates.

On nine newer papers: 78/225 answers remain unresolved (v5: 83). In the independent
assistant-read subset of 49 clear answers, 34 matched, 15 remained unresolved and
none differed. One additional ambiguous multi-mark answer remained unresolved.
These are assistant references, not client-approved ground truth. Handwritten
identity OCR is unchanged. Current exception rates still FAIL unattended bulk
readiness; no claim of perfect recognition or 2,500-student automatic approval.

For the same nine papers, marks and identity inference took 24.22 seconds with
one worker and 15.95 seconds with two; answers/fields were identical. Maximum
single-child resident memory was 456,310,784 bytes on macOS. Timing includes
worker preparation and local evidence output but excludes hosted database and
network overhead. Concurrency is a throughput change, not an accuracy measure.

Passed 29 mark/API/audit/operations/colour/concurrency tests and the separate
bulk API restart test. The local app was restarted with a dedicated two-worker
processor. Its nine unapproved papers were re-read through the authenticated
API, preserving edits/approvals via the existing compare-and-swap audit path.
The updated batch was verified in the browser. The public Render deployment
has not been verified or updated by these local steps.

An additional full-width grayscale promotion experiment produced two wrong
choices in the reviewed calibration set and was rejected. It is not shipped.
