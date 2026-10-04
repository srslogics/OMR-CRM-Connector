"""Optional, local-only handwriting reader for a dedicated Apple Silicon worker.

Disabled unless PAPERDESK_VISION_MODEL_DIR is set. No API, cloud upload, key,
answer key, identity lookup or automatic verification. Scores are not invented.
"""
import os
import re
import threading
from pathlib import Path
import logging

MODEL_ID = 'mlx-community/Qwen3-VL-2B-Instruct-4bit'
MODEL_REVISION = '9c4f5209e57b31f4b9dfba735de3fb983739c9cc'
PROMPT = ('Transcribe ONLY the handwritten text in these boxes, reading left to right. '
          'Ignore the printed grid. Do not guess, correct spelling, complete words, or add missing digits. '
          'Return only the text. If the boxes contain no handwriting return BLANK. '
          'If handwriting cannot be read return UNREADABLE.')
PRIMARY_FIELDS = {'name','school','class','taluka'}
_lock = threading.Lock()
_engine = None
_failed = False


def configured():
    return bool(os.getenv('PAPERDESK_VISION_MODEL_DIR','').strip())


def engine():
    global _engine
    if _engine is None:
        path = Path(os.environ['PAPERDESK_VISION_MODEL_DIR']).expanduser().resolve()
        if not path.is_dir() or not (path/'model.safetensors').is_file():
            raise ValueError('Local vision model is not installed')
        # Prevent the library from resolving/downloading missing files at runtime.
        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
        os.environ['TOKENIZERS_PARALLELISM'] = 'false'
        from mlx_vlm import load
        from mlx_vlm.utils import load_config
        config = load_config(str(path))
        if config.get('model_type') != 'qwen3_vl' or config.get('text_config',{}).get('hidden_size') != 2048:
            raise ValueError('Use the pinned Qwen3-VL 2B model')
        model,processor = load(str(path))
        _engine = model,processor,config
    return _engine


def transcribe(image):
    global _failed
    if not configured() or _failed:
        return None
    try:
        with _lock:
            model,processor,config = engine()
            from mlx_vlm import generate
            from mlx_vlm.prompt_utils import apply_chat_template
            from PIL import Image
            import cv2
            import mlx.core as mx
            if image.shape[0] < 3 or image.shape[1] < 3:
                return None
            prompt = apply_chat_template(processor,config,PROMPT,num_images=1)
            pixels = Image.fromarray(cv2.cvtColor(image,cv2.COLOR_BGR2RGB))
            try:
                result = generate(model,processor,prompt,[pixels],max_tokens=70,temperature=0,verbose=False)
                return clean_output(result.text)
            finally:
                mx.clear_cache()
    except Exception as error:
        # Disable a broken model for this worker session; preserve the fast reader.
        _failed = True
        logging.warning('Local vision OCR unavailable (%s); fast OCR retained.',type(error).__name__)
        return None


def clean_output(value):
    value = str(value).strip()
    value = re.sub(r'^```(?:text|markdown)?\s*|\s*```$','',value,flags=re.I).strip()
    if value.upper() in ('BLANK','UNREADABLE','UNKNOWN'):
        return ''
    if not value or len(value)>180 or '\n' in value or any(c in value for c in '{}<>'):
        return None
    return value


def merge_reading(reading, text, key):
    """Keep human decisions separate; model agreement is evidence, not identity proof."""
    if text is None:
        return reading
    from student_details import normalise
    text = normalise(text,key)
    primary = reading.get('suggested','')
    out = {**reading,'candidates':[dict(c) for c in reading.get('candidates',[])]}
    out['vision'] = {'text':text,'model':MODEL_ID,'revision':MODEL_REVISION}
    norm = lambda value: ''.join(value.casefold().split())
    agreement = bool(primary and text and norm(primary)==norm(text))
    out['reader_agreement'] = agreement
    if text and not any(norm(c['text'])==norm(text) for c in out['candidates']):
        out['candidates'].append({'text':text,'method':'Local vision reader','score':None})
    valid_class = key!='class' or re.fullmatch(r'(?:[1-9]|1[012]|[IVX]{1,4})(?:st|nd|rd|th)?',text,re.I)
    # Do not replace an apparent blank with generated text. Keep it as an alternative.
    if key in PRIMARY_FIELDS and text and valid_class and primary:
        out['suggested'] = text
    out['engine'] = reading.get('engine','Local OCR')+' + Qwen3-VL 2B (local)'
    if agreement:
        out.update(state='review',reason='Two local readers agree. This has not verified the student identity.')
    elif text != primary:
        out.update(state='conflict',reason='Local OCR and the vision reader disagree. Both readings are retained beside the scan.')
    return out


def refine_name_reading(reading, text):
    """Second literal name reading; keep source alternatives and verification pending."""
    if text is None:
        return reading
    from student_details import normalise
    text = normalise(text, 'name')
    out = {**reading, 'candidates': [dict(c) for c in reading.get('candidates', [])]}
    out['name_grid_vision'] = {'text': text, 'model': MODEL_ID, 'revision': MODEL_REVISION}
    if not text or not reading.get('suggested'):
        return out
    if not any(''.join(c['text'].casefold().split()) == ''.join(text.casefold().split()) for c in out['candidates']):
        out['candidates'].append({'text': text, 'score': None, 'method': 'Local vision — grid removed'})
    out['suggested'] = text
    out['state'] = 'review' if text == reading['suggested'] else 'conflict'
    out['reason'] = 'Name read with printed grid removed. Original alternatives remain available; identity is not verified.'
    return out
