# PaperDesk — Examination evaluation by SrS Logics

A working first version for combined-PDF examination processing. Python/FastAPI backend, SQLite records and queue, private file storage, OpenCV template registration and mark detection, and a responsive browser interface.

## Run

Requires Python 3.11+ (tested on 3.13). Run the commands from this repository’s `paperdesk/` folder. An internet connection is needed for the initial dependency installation.

macOS/Linux:

```sh
./start.sh
```

Or, on any supported platform:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python setup_ocr.py
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 4180 --workers 1
```

On Windows, use `.venv\Scripts\python.exe` in place of `.venv/bin/python`.

Open http://127.0.0.1:4180. Create your administrator account on first launch. No default password, SMS provider, API key, or paid OCR account is required.

## Try the workflow

Use **Try a synthetic sample batch** on the overview. This generates a blank master, mapped answer regions, a synthetic key and a six-page PDF for three fictional students. It runs the real processing pipeline. The fixture is explicitly labelled synthetic, not the client's examination.

Expected provisional scores: first student 100; second 76; third 92 with one blank and one unresolved double mark. Review student details, both scans and every answer, then approve. Excel/CSV exports only contain approved papers. Each approved paper has a downloadable PDF marksheet.

## Evaluate your own PDFs

1. Create an exam with its name and class. Each class/paper layout has its own template.
2. Enter all 25 answers from the official key.
3. Upload a blank two-page PDF master. Map each answer region in A/B/C/D order by dragging rectangles on the scan. Include enough margin for a tick, while excluding neighbouring answers. Map all eight student fields on page 1: name, school, class, section, taluka, district, father’s mobile and mother’s mobile. Include the full character boxes; exclude printed field labels. Unmapped fields remain visibly unavailable and need manual entry.
4. Save and verify the map and key. Lock the exam. Locked settings cannot change; create a new exam for another key or layout.
5. Upload a combined PDF: two consecutive pages per student, no covers. Limits: 30 pages/15 students (MVP), 150 MB. Odd page counts, encrypted or invalid PDFs are rejected.
6. Processing runs in a persistent queue on the server, one student at a time. Closing the browser does not stop it. Unprocessed work resumes after restart. A failed batch can be retried without overwriting reviewed papers.
7. Review **Student details** first. Each mapped field has its original aligned crop, editable text and OCR alternatives. Enlarge a crop, correct the value and choose **Confirmed from scan**. Use **Blank on paper** only for an empty field, or **Unreadable / incomplete** when it cannot be recovered. These two choices clear the value and retain an explicit status. Changing a confirmed value resets its confirmation.
8. Check that both pages belong to the student and save. **Save & next student** speeds up the batch. Once all eight fields have a recorded decision and the name is confirmed, **Student details Excel / CSV** can export the record even while marks are under review. Exports include source pages, a paper ID and a separate status for every field. Phone numbers remain text in Excel.
9. Review all answers against the scans. Uncertain marks remain `?`; blanks use `-`. Approve only after checking all answers and student details. Download **Results Excel / CSV** and individual PDF marksheets after approval. Corrections have an audit record; concurrent edits cannot silently overwrite each other.

Scoring: Q1–10 Science /40, Q11–20 Mathematics /40, Q21–25 Mental Ability /20. Four marks for an exact key match, zero otherwise, no negative marking. Unresolved answers prevent approval.

## Recognition and limits

- The answer reader is real computer vision, not simulated results. It registers each page to the blank master and measures added ink in mapped answer areas. Multiple and faint marks are flagged. Misaligned pages require manual review.
- Student extraction uses a pinned English PP-OCRv5 mobile recognizer from RapidAI/PaddleOCR, running locally through ONNX Runtime. It keeps higher-resolution handwriting crops and compares original, grid-suppressed and cell-interior readings. `setup_ocr.py` downloads the model once and verifies its SHA-256; the Docker build and `start.sh` run this step automatically. Processing itself makes no cloud OCR requests. The original RapidOCR/Tesseract path remains a fallback if the enhanced model is missing. See `third_party/README.md` for attribution.
- These are suggestions, never verified identity. A 10-paper local calibration comparison improved exact matches from 2/65 to 40/65 clearly readable filled fields. Three additional blank fields were correctly left empty; 12 ambiguous/incomplete fields were excluded. The same papers were used during development, so this is not independent accuracy validation. Names and school names still need frequent corrections. Marathi handwriting has not been validated. See `VALIDATION.md`.
- No field is automatically confirmed. A confirmed mobile must contain exactly 10 digits; OCR does not replace letters with digits or invent missing digits. The expected exam class is displayed separately, not silently copied into the extracted student class.
- If no OCR engine is available, mark detection still works; student details can be entered manually.
- Perspective alignment is supported. Strong page curl, erasures, photocopy noise, shifted printing and handwritten corrections are not reliably resolved automatically. Model scores rank alternatives; they are not calibrated probabilities that a student identity is correct.
- Sequential pairing cannot establish ownership of an unlabelled second page if same-format pages are mixed. Staff must verify pairing. Future papers should include a student/page ID on every page.
- A Class 10 blank master, supplied official key and 10-paper pilot were calibrated locally. Real scans, transcriptions, answer maps and provisional scores are private working files and are not seeded or committed in this repository. Each new class/layout still needs its own checked map and key.
- Automated integration checks cover a synthetic three-student batch; the MVP permits up to 15 students per batch. Start with 10; scan variation and Render Free performance still require client validation.

## Existing papers and upgrades

New batches use the improved reader automatically when its model is installed. On an existing paper, **Read details again** saves the current draft and reads from the original PDF. It refreshes suggestions and crops while preserving saved manual edits and confirmations. Existing unconfirmed text is retained unless it is empty or still equals its previous OCR suggestion; choose a new alternative explicitly when needed. Rereading returns the result to review. All eight field confirmations are required before older approved records can be exported again.

For Render with the included Dockerfile, deploy the latest repository commit; the model is installed during the build. For a native Python service with root directory `paperdesk`, use `pip install -r requirements.txt && python setup_ocr.py` as the build command. The MVP still allows at most **15 students / 30 pages** per batch. No paid OCR account or hosting upgrade is introduced. Runtime performance on Render Free has not been measured. Its temporary filesystem does not provide durable storage: export and back up before redeploying.

## Storage and deployment

By default, data is stored under `data/` beside the application, not in browser storage. Set `PAPERDESK_DATA` to a private persistent directory to change this. Back up the SQLite database and stored PDFs/images together while the process is stopped. Data is protected by application login, not encrypted at rest by this app.

The preview is local. This processing service cannot be hosted as a static site. The included Dockerfile is a starting point for a Python-capable server with a persistent disk. Run exactly **one worker/process and one replica** with this SQLite queue. Do not scale replicas until queue coordination and database storage are redesigned. Keep the data directory private, use HTTPS, set `COOKIE_SECURE=1`, and complete first-account setup before exposing an instance to other users. Establish backups, retention/deletion rules, monitoring and real-batch validation before a production launch.

## Tests

```sh
.venv/bin/python -m pip install httpx
.venv/bin/python test_app.py
```

Tests use isolated temporary storage and generated papers. They verify login, protected media, cross-origin rejection, immutable keys, odd-page rejection, mark reading, ambiguous answer handling, scoring, review gates, conflict handling, exports and audit records. `requirements.lock.txt` records the development environment.

## Uptime monitoring

Use an HTTP(S) monitor with URL `https://YOUR-SERVICE.onrender.com/`. The public homepage supports both GET and HEAD, so UptimeRobot’s default HEAD check works without changing the method. This checks HTTP availability only; it does not verify completion of paper processing or preserve data on Render Free.


### Durable storage on Render Free

Set `DATABASE_URL` in Render's Environment settings to a PostgreSQL direct or **session pooler** connection (port 5432). URL-encode special characters in the password. Never commit this value. Render deployments require this setting; the application refuses to silently start an empty temporary SQLite workspace.

PaperDesk creates an isolated `paperdesk` schema. Accounts, sessions, exams, results and private document bytes are saved in PostgreSQL. Local files are disposable caches and are recovered on demand after redeployment. For this small MVP, documents are stored transactionally in the same database, not in a public bucket. The default file budget is 180 MiB (`PAPERDESK_FILE_BUDGET_MB`); this is an application limit, not a guarantee against provider database quotas. Monitor database usage. Larger workloads should move document bytes to private object storage.

The connection must support session advisory locks; do not use a transaction pooler on port 6543. Keep one application worker. Render Free can still sleep, but PostgreSQL records survive replacement of the Render container. Missing or failed database connections never fall back to an empty account database. Previously erased SQLite data cannot be recovered by this change; restore from a backup if available.

For a disposable isolated PostgreSQL test schema, set `PAPERDESK_DB_SCHEMA=paperdesk_test_<hex>` and run `test_persistence.py` and `test_app.py` separately with fresh schemas. Tests use only synthetic documents.

## Bulk intake (processing-team workflow)

The Upload papers form accepts one combined PDF per exam, up to 6,000 pages and
150 MB per upload. It checks the page-count bounds and requires confirmation of
one class/template and two consecutive pages per student. It does not reliably
detect mixed classes, missing middle pages or substituted students automatically.

Large uploads are divided into 30-page parts and committed as one import. The
worker uses bounded concurrency (one process by default) and skips already-saved papers after a
restart. Re-uploading the identical bytes to the same exam returns the existing
queue; it does not create duplicates. A failed intake rolls back all its parts.
Original source-page ranges are included in each part's name.

On PostgreSQL, intake checks the configured document budget, saved bytes and
pending work before accepting the import. It reserves an estimate of 3 MiB per
student for generated evidence in addition to the source PDF. Actual writes still
obey the hard budget. The default 180 MiB budget cannot hold the supplied 596 MiB
archive, even without generated evidence. Do not increase the configured budget
beyond actual available storage. Local installations use their own disk; they
are separate workspaces unless explicitly connected to the hosted database.

Bulk intake does not automatically approve answers or identities. Processing-team
staff resolve exceptions, verify page pairing, and release reviewed results.
Client-approved pilot records are preserved. Capacity and queue tests are separate
from the scan-accuracy benchmark in VALIDATION.md.

### Processing desk

Use **Processing desk** for the processing team's workload across all batches.
Open an item, inspect the scan, correct the flagged fields/answers and save the
draft back to the queue. Final approval still checks the saved values and page
pairing. Client results exports contain approved records only. This view shares
the existing administrator login; it is not a separate permission boundary.

The desk also shows failed/queued jobs and hosted document capacity, including
estimated space reserved for unfinished papers. Resolve capacity before intake;
do not raise the application allowance past the provider's actual quota.

### Separate web and processing workers

The web process can serve the interface without running OCR. Set
`PAPERDESK_EMBEDDED_WORKER=0` for it, and start a separate process from this
`paperdesk` directory:

```sh
PAPERDESK_PROCESS_WORKERS=2 .venv/bin/python worker.py
```

Both processes must use the same `DATABASE_URL` and schema, or the same absolute
`PAPERDESK_DATA` directory on a local installation. A PostgreSQL advisory lock
(or a local filesystem lock on macOS/Linux) permits only one queue coordinator.
The coordinator schedules at most one student per configured child process,
checkpoints each finished student, and resumes without replacing saved records.
`PAPERDESK_PROCESS_WORKERS` accepts 1–4; the default is 1. Child processes perform
image/OCR work only; the coordinator owns database writes. Ctrl+C/SIGTERM stops
new scheduling and drains the bounded work already in flight.

Measured locally on nine real Class 10 papers, two workers took 15.95 seconds
versus 24.22 seconds for one, with identical extracted answers and fields. This
is a small local test, not a 2,500-student hosting benchmark. A child process
reached approximately 435 MiB of resident memory. Use at least 2 GiB available
memory for two processing workers plus the coordinator and web process, then
measure actual usage. Do not enable two OCR processes on a 512 MiB instance.
A separate process must actually be running; disabling the embedded worker alone
leaves jobs queued. Hosting plan availability and storage quotas are independent
of these software settings.

Run concurrency and restart checks separately from tests that initialise their
own temporary database:

```sh
.venv/bin/python -m unittest test_parallel_worker
.venv/bin/python -m unittest test_bulk_api
```

### Reader v7 validation

The reader now retries residual page deformation and long ticks that extend
outside the answer box. It compares the original and corrected readings and
retains conflicts for review, including a long tick alongside a crossed-out
choice. The answer key is used only after recognition for scoring.

`python -m unittest test_refinement` checks geometry and conflict behaviour.
See `VALIDATION.md` for the measured scan results and remaining limitations.
The student handwriting engine is unchanged: tested replacements did not improve
these scans. The new mark reader does not automatically approve student identity
or make the 2,610-student archive ready for unattended release.

Reader v7's latest marks-only test peaked at about 532 MiB for one process,
excluding full identity OCR and hosting overhead. A 512 MiB service has
insufficient headroom for this tested path. Keep the web process separate and
run the processing worker on a machine with adequate memory; do not raise
concurrency on the small web instance to compensate for accuracy work.

### Reader v8 and optional handwriting worker

See [RECOGNITION_V8.md](RECOGNITION_V8.md) for measured improvements and remaining
errors. The bundled numeric Class 10 ink model runs without extra runtime
packages, only when the uploaded master and mapping match its trained scope.
It preserves uncertain answers and does not enable automatic approval.

For the optional **Apple Silicon local worker**, install the usual requirements
and `requirements-vision.txt` into a dedicated environment, then download the
pinned public model (this does not upload any papers):

```sh
python -m pip install -r requirements.txt -r requirements-vision.txt
python setup_vision.py --directory /absolute/path/to/qwen3-vl-2b
PAPERDESK_VISION_MODEL_DIR=/absolute/path/to/qwen3-vl-2b PAPERDESK_PROCESS_WORKERS=1 python worker.py
```

Use the same data/database configuration as the web service. Set
`PAPERDESK_EMBEDDED_WORKER=0` on that web service when using a separate worker.
Do not set the vision-model variable on the Render Linux web process. Without
this variable, the existing lightweight OCR path remains active. A failed vision
load retains that OCR path and records a warning; it does not invent a result.
Allow at least 4 GiB spare memory for the local worker and measure usage before
scheduling bulk work. The local vision path has been tested with one process.
