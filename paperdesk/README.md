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
