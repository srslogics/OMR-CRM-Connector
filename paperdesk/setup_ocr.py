"""Install the pinned local recognizer. No student files are read or uploaded."""
from pathlib import Path
import hashlib
import os
import urllib.request

MODEL = Path(__file__).parent / 'models' / 'en-rec.onnx'
SHA256 = 'c3461add59bb4323ecba96a492ab75e06dda42467c9e3d0c18db5d1d21924be8'
URL = 'https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.9.2/onnx/PP-OCRv5/rec/en_PP-OCRv5_rec_mobile.onnx'

def install():
    if MODEL.exists() and hashlib.sha256(MODEL.read_bytes()).hexdigest() == SHA256:
        return
    MODEL.parent.mkdir(parents=True, exist_ok=True)
    temporary = MODEL.with_suffix('.download')
    try:
        with urllib.request.urlopen(URL, timeout=120) as source, temporary.open('wb') as target:
            while chunk := source.read(1024 * 1024):
                target.write(chunk)
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != SHA256:
            raise RuntimeError('Student OCR model checksum did not match; installation stopped.')
        os.replace(temporary, MODEL)
    finally:
        temporary.unlink(missing_ok=True)
    print('Local student-detail recognizer installed.')

if __name__ == '__main__':
    install()
