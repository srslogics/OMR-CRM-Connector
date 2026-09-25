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
3. Upload a blank two-page PDF master. Map each answer region in A/B/C/D order by dragging rectangles on the scan. Include enough margin for a tick, while excluding neighbouring answers. Map handwritten student fields on page 1 if using OCR.
4. Save and verify the map and key. Lock the exam. Locked settings cannot change; create a new exam for another key or layout.
5. Upload a combined PDF: two consecutive pages per student, no covers. Limits: 600 pages/300 students, 150 MB. Odd page counts, encrypted or invalid PDFs are rejected.
6. Processing runs in a persistent queue on the server, one student at a time. Closing the browser does not stop it. Unprocessed work resumes after restart. A failed batch can be retried without overwriting reviewed papers.
7. Review each paper. The aligned scan and original PDF are available. Uncertain marks remain `?`; blanks use `-`. All papers require an explicit student-detail and page-pairing check before approval. Corrections have an audit record; concurrent edits cannot silently overwrite each other.
8. Download approved results as Excel/CSV and individual PDF marksheets.

Scoring: Q1–10 Science /40, Q11–20 Mathematics /40, Q21–25 Mental Ability /20. Four marks for an exact key match, zero otherwise, no negative marking. Unresolved answers prevent approval.

## Recognition and limits

- The answer reader is real computer vision, not simulated results. It registers each page to the blank master and measures added ink in mapped answer areas. Multiple and faint marks are flagged. Misaligned pages require manual review.
- RapidOCR runs on the local computer with models included in its installed package; student scans are not sent to an external OCR service. Tesseract on PATH is a fallback. OCR suggestions are never verified identity. Printed Latin text is tested on the synthetic sample; handwriting and Marathi recognition are not validated in this release.
- If no OCR engine is available, mark detection still works; student details can be entered manually.
- Perspective alignment is supported. Strong page curl, erasures, photocopy noise, shifted printing and handwritten corrections are not reliably resolved automatically. There is no accuracy guarantee or confidence calibration on the client's papers yet.
- Sequential pairing cannot establish ownership of an unlabelled second page if same-format pages are mixed. Staff must verify pairing. Future papers should include a student/page ID on every page.
- The official answer key and representative combined client PDF have not been supplied. Templates from the client's photographs have not been pre-calibrated, and no real student scores are seeded.
- Automated integration checks cover a synthetic three-student batch; full 300-student processing time, scan variation and memory/disk sizing must be measured before production use.

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
