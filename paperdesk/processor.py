"""Conservative template-aligned mark reading. All papers require human approval."""
from pathlib import Path
import json, shutil, subprocess, importlib.util, logging
import cv2
import numpy as np
import pymupdf as fitz

FIELDS=['name','school','class','section','taluka','district','father_mobile','mother_mobile']

def raster(page):
    pix=page.get_pixmap(matrix=fitz.Matrix(1.7,1.7),alpha=False)
    rgb=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3)
    return cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR)

def align(image, template):
    """Return aligned pixels only when there is sufficient geometric evidence."""
    orb=cv2.ORB_create(6000)
    k1,d1=orb.detectAndCompute(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY),None)
    k2,d2=orb.detectAndCompute(cv2.cvtColor(template,cv2.COLOR_BGR2GRAY),None)
    if d1 is None or d2 is None:return None,0
    matches=cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(d1,d2,k=2)
    good=[m[0] for m in matches if len(m)==2 and m[0].distance<.72*m[1].distance]
    if len(good)<18:return None,0
    a=np.float32([k1[m.queryIdx].pt for m in good]); b=np.float32([k2[m.trainIdx].pt for m in good])
    H,mask=cv2.findHomography(a,b,cv2.RANSAC,3.5)
    quality=float(mask.mean()) if mask is not None else 0
    if H is None or quality<.45 or int(mask.sum())<16:return None,quality
    ih,iw=image.shape[:2]; th,tw=template.shape[:2]
    corners=cv2.perspectiveTransform(np.float32([[[0,0],[iw,0],[iw,ih],[0,ih]]]),H)[0]
    area=abs(cv2.contourArea(corners)); expected=th*tw
    if not .55<area/expected<1.7 or not cv2.isContourConvex(corners):return None,quality
    return cv2.warpPerspective(image,H,(tw,th),borderValue=(255,255,255)),quality

def crop(im,r):
    h,w=im.shape[:2];x,y,rw,rh=r
    return im[max(0,int(y*h)):min(h,int((y+rh)*h)),max(0,int(x*w)):min(w,int((x+rw)*w))]

def detect_question(image,template,regions):
    # Ignore small registration noise by subtracting an expanded template ink mask.
    vals=[]
    for r in regions:
        a=crop(image,r);b=crop(template,r)
        if a.size==0 or b.size==0:return {'answer':'?','reason':'Invalid answer region','evidence':[]}
        ag=cv2.cvtColor(a,cv2.COLOR_BGR2GRAY);bg=cv2.cvtColor(b,cv2.COLOR_BGR2GRAY)
        ink=ag<155; old=cv2.dilate((bg<175).astype('uint8'),np.ones((3,3),np.uint8))>0
        new=(ink & ~old).astype('uint8');n,_,stats,_=cv2.connectedComponentsWithStats(new,8)
        largest=int(max(stats[1:,cv2.CC_STAT_AREA],default=0))
        vals.append({'ratio':round(float(new.mean()),4),'pixels':largest})
    marked=[i for i,v in enumerate(vals) if v['ratio']>=.025 and v['pixels']>=8]
    faint=any(v['ratio']>=.009 and v['pixels']>=4 for v in vals)
    if len(marked)==1:answer='ABCD'[marked[0]];reason='One detected mark; verify against scan'
    elif len(marked)>1:answer='?';reason='Multiple marks or correction'
    elif faint:answer='?';reason='Faint or uncertain mark'
    else:answer='-';reason='No mark detected; verify blank'
    return {'answer':answer,'reason':reason,'evidence':vals}

_ocr_engine = None

def ocr_available():
    return importlib.util.find_spec('rapidocr_onnxruntime') is not None or bool(shutil.which('tesseract'))

def ocr_crop(im, region, directory, key):
    """Local text suggestions only; never authoritative student identity."""
    global _ocr_engine
    cut=crop(im,region)
    if not cut.size:return ''
    if importlib.util.find_spec('rapidocr_onnxruntime') is not None:
        try:
            import onnxruntime
            onnxruntime.disable_telemetry_events()
            from rapidocr_onnxruntime import RapidOCR
            if _ocr_engine is None:_ocr_engine=RapidOCR(width_height_ratio=-1,det_limit_type="max",det_limit_side_len=960,det_model_path=None)
            padded=cv2.copyMakeBorder(cut,16,16,16,16,cv2.BORDER_CONSTANT,value=(255,255,255))
            result,_=_ocr_engine(padded)
            return ' '.join(str(row[1]) for row in (result or []) if float(row[2])>=.6).strip()
        except Exception as exc:
            logging.warning('Local OCR failed; student details require manual entry: %s',type(exc).__name__)
    if not shutil.which('tesseract'):return ''
    target=Path(directory)/f'ocr-{key}.png';cv2.imwrite(str(target),cut)
    try:
        r=subprocess.run(['tesseract',str(target),'stdout','--psm','7'],capture_output=True,text=True,timeout=20)
        return r.stdout.strip() if r.returncode==0 else ''
    except (subprocess.TimeoutExpired, OSError):return ''
    finally:target.unlink(missing_ok=True)

def score(answers,key):
    if len(answers)!=25 or len(key)!=25:raise ValueError('25 answers and key entries are required')
    if any(a not in ['A','B','C','D','-','?'] for a in answers):raise ValueError('Invalid answer')
    parts=[sum(4 for i in range(lo,hi) if answers[i]==key[i]) for lo,hi in [(0,10),(10,20),(20,25)]]
    return {'science':parts[0],'mathematics':parts[1],'mental_ability':parts[2],'total':sum(parts),'correct':sum(a==k for a,k in zip(answers,key)),'blank':answers.count('-'),'unresolved':answers.count('?')}

def validate_config(conf):
    if len(conf.get('key',[]))!=25 or any(not isinstance(a,str) or len(a)!=1 or a not in 'ABCD' for a in conf['key']):raise ValueError('Enter all 25 correct answers before locking the exam.')
    mapping=conf.get('mapping',{})
    if set(mapping)!=set(str(i) for i in range(1,26)):raise ValueError('Map all 25 questions before locking.')
    for q,m in mapping.items():
        if m.get('page') != (0 if int(q)<=10 else 1):raise ValueError('Questions 1-10 belong to page 1; 11-25 to page 2.')
        if len(m.get('boxes',[]))!=4:raise ValueError('Each question needs four answer regions, in A/B/C/D order.')
        for r in m['boxes']:validate_rect(r)
    for name,m in conf.get('fields',{}).items():
        if name not in FIELDS or m.get('page')!=0:raise ValueError('Invalid student field')
        validate_rect(m['box'])

def validate_rect(r):
    if not isinstance(r,list) or len(r)!=4 or any(not isinstance(v,(int,float)) or not np.isfinite(v) for v in r):raise ValueError('Invalid rectangle')
    x,y,w,h=r
    if min(x,y)<0 or w<=0 or h<=0 or x+w>1.001 or y+h>1.001:raise ValueError('Region is outside the page')
