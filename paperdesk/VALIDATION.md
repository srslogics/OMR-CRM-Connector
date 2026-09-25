# Validation record

Verified locally on 25 September 2026 with Python 3.13.

- Generated six-page PDF, three fictional students, processed through the real image pipeline.
- Expected scores reproduced: 100, 76, and 92 provisional (one blank and one unresolved double mark).
- Printed student-name extraction checked against the generated source.
- Authentication, protected files, same-origin writes, template locking, odd-page rejection, review gates, stale-edit protection, approved-only CSV/Excel exports, audit records and PDF marksheets checked.
- Browser review and approval checked using synthetic data. Marksheet rendered and visually inspected.

These checks do not establish accuracy on handwritten client papers. A representative combined PDF, blank two-page masters for each layout, and official answer keys are still needed for calibration and acceptance testing. The MVP upload limit is 15 students (30 pages) per batch. A generated 15-student batch is tested locally, and a 16-student upload is rejected. This is not a performance guarantee for real scans or Render Free.
