# Recognition v8 — 4 October 2026

## Implemented

The answer reader combines registered checkbox evidence, complete option-row ink,
multiple resolutions, tick geometry and a compact ExtraTrees classifier. It never
receives the official correct answer during recognition. The classifier only
recovers unresolved answers for the exact master and region map used in training.
Conflicting readers, unsupported alignment and competing marks still abstain.
Recovered answers remain reviewable; forest scores are not calibrated confidence.

The model asset is plain numeric JSON, with no executable pickle or student text.
`train_mark_model.py` trains offline and validates with entire students held out.
Training requires scikit-learn; production inference does not.

Optional local Qwen3-VL 2B handwriting recognition supplements PP-OCRv5. Both
readings remain beside the scan. Name, school, class and taluka may use the vision
suggestion; phone numbers retain the original reader. Agreement never verifies an
identity. Approved records reject rereading; manual corrections remain protected.

## Measurements and limits

On nine additional Class 10 papers (225 answers), 210 references were clear and
15 ambiguous. V8 matched 180 clear references, left 30 clear references unresolved,
and left all 15 ambiguous references unresolved. No selected answer differed from
a clear reference. Total unresolved fell from v7's 70 to 45. These are assistant
visual references, not client-approved labels. Seven papers informed development;
only two papers were newly labelled before viewing the frozen model's predictions.
On those two papers, correct readings increased from 37 to 45 of 50, with five
unresolved and no observed wrong selection. This small sample does not establish
an unattended error rate. Unresolved counts are not total review-work counts.

The same nine papers contain 72 student fields: 60 readable filled, six blank,
and six ambiguous/excluded. In the actual local application's saved records,
exact matches improved from 38/66 to 44/66, including all six blank fields.
Therefore filled-field exact matches improved from 32/60 to 38/60. Case and
whitespace are ignored; names and phone digits otherwise must match exactly.
Twenty-two evaluated fields still fail exact matching. No automatic identity
approval or bulk release is justified by this result.

The nine-student local app batch completed and all 72 fields include vision
provenance. Its sequential detail reread took 76.91 seconds. This is a local M1
measurement, not hosted throughput. The vision model alone uses roughly 2 GiB;
use a dedicated Apple Silicon worker with adequate spare memory, one process.
The optional MLX reader does not run on Render's Linux web instance.

## Alternatives actually tested locally

On 75 client-confirmed readable calibration fields, Qwen3-VL 2B matched 48,
Qwen3-VL 4B 45, and GLM-OCR 36 after output cleanup. Larger was not better.
Apple Vision and PP-OCRv5 server variants did not beat the existing reader.
TrOCR-small also performed poorly on these boxed handwritten fields. These are
calibration comparisons, not general model rankings. Qwen's focused mark trial
made four wrong selections out of 125 questions; it is not used to grade answers.
No student scans were uploaded to an external model provider.

Primary documentation:
- https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.ExtraTreesClassifier.html
- https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.LeaveOneGroupOut.html
- https://github.com/Blaizzy/mlx-vlm
- https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct
- https://huggingface.co/zai-org/GLM-OCR
- https://paddlepaddle.github.io/PaddleOCR/main/en/version3.x/module_usage/text_recognition.html

## Release status

Local validation build, not an unattended bulk release. Before bulk release,
measure answer errors, exact identity-field errors and actual exception workload
on untouched papers from different source files, schools and scan conditions.
The current improvement does not meet the requested small exception rate.
Private references, scans, predictions and intermediate training files are kept
outside this repository. Production records were not modified by these trials.
