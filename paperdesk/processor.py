"""Conservative template-aligned mark reading. All papers require human approval."""
from pathlib import Path
import json, shutil, subprocess, importlib.util, logging
import cv2
import numpy as np
import pymupdf as fitz

FIELDS=['name','school','class','section','taluka','district','father_mobile','mother_mobile']

def raster(page, zoom=1.7):
    pix=page.get_pixmap(matrix=fitz.Matrix(zoom,zoom),alpha=False)
    rgb=np.frombuffer(pix.samples,np.uint8).reshape(pix.height,pix.width,3)
    return cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR)

def align(image, template, return_transform=False):
    """Return aligned pixels only when there is sufficient geometric evidence."""
    def result(pixels, quality, transform=None):
        return (pixels,quality,transform) if return_transform else (pixels,quality)
    orb=cv2.ORB_create(6000)
    k1,d1=orb.detectAndCompute(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY),None)
    k2,d2=orb.detectAndCompute(cv2.cvtColor(template,cv2.COLOR_BGR2GRAY),None)
    if d1 is None or d2 is None:return result(None,0)
    matches=cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(d1,d2,k=2)
    good=[m[0] for m in matches if len(m)==2 and m[0].distance<.72*m[1].distance]
    if len(good)<18:return result(None,0)
    a=np.float32([k1[m.queryIdx].pt for m in good]); b=np.float32([k2[m.trainIdx].pt for m in good])
    H,mask=cv2.findHomography(a,b,cv2.RANSAC,3.5)
    quality=float(mask.mean()) if mask is not None else 0
    if H is None or quality<.45 or int(mask.sum())<16:return result(None,quality)
    ih,iw=image.shape[:2]; th,tw=template.shape[:2]
    corners=cv2.perspectiveTransform(np.float32([[[0,0],[iw,0],[iw,ih],[0,ih]]]),H)[0]
    area=abs(cv2.contourArea(corners)); expected=th*tw
    if not .55<area/expected<1.7 or not cv2.isContourConvex(corners):return result(None,quality)
    return result(cv2.warpPerspective(image,H,(tw,th),borderValue=(255,255,255)),quality,H)

def detail_pixels(page, low_image, template, transform):
    """Reuse validated registration while retaining more handwriting pixels."""
    high=raster(page,3.4)
    ih,iw=low_image.shape[:2];hh,hw=high.shape[:2];th,tw=template.shape[:2]
    scaled=np.diag([2.,2.,1.]) @ transform @ np.diag([iw/hw,ih/hh,1.])
    pixels=cv2.warpPerspective(high,scaled,(tw*2,th*2),borderValue=(255,255,255))
    return pixels,cv2.resize(template,(tw*2,th*2))

def crop(im,r):
    h,w=im.shape[:2];x,y,rw,rh=r
    return im[max(0,int(y*h)):min(h,int((y+rh)*h)),max(0,int(x*w)):min(w,int((x+rw)*w))]

MARK_READER_VERSION = 7

def ink_contrast(image):
    """Remove slow lighting/shadow changes without inventing missing strokes."""
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    size=max(9,round(image.shape[1]/1100*19))|1
    background=cv2.morphologyEx(gray,cv2.MORPH_CLOSE,np.ones((size,size),np.uint8))
    return cv2.subtract(background,gray)

def detect_question_legacy(image,template,regions,prepared=None):
    """Read scan evidence only. The answer key is deliberately not an input.

    Global registration cannot compensate for every curved page. Match nearby
    printed structure, subtract normalized print, and require ink inside a box
    so a long tick tail does not select the option above it. Abstain on blanks:
    an invisible/faint/off-box mark is not evidence of an unanswered question.
    """
    unknown=lambda reason: {'answer':'?','reason':reason,'evidence':[]}
    if image.shape[:2]!=template.shape[:2] or len(regions)!=4:
        return unknown('Answer areas do not match this scan; check the template.')
    a,b=prepared if prepared is not None else (ink_contrast(image),ink_contrast(template))
    h,w=a.shape;scale=w/1100
    boxes=[(int(x*w),int(y*h),int((x+rw)*w),int((y+rh)*h)) for x,y,rw,rh in regions]
    search=max(3,round(8*scale));pad=max(10,round(22*scale))
    x1=max(search,min(r[0] for r in boxes)-pad);y1=max(search,min(r[1] for r in boxes)-pad)
    x2=min(w-search,max(r[2] for r in boxes)+pad);y2=min(h-search,max(r[3] for r in boxes)+pad)
    if x2<=x1 or y2<=y1:return unknown('Invalid answer area; check the template.')
    ref=b[y1:y2,x1:x2];src=a[y1-search:y2+search,x1-search:x2+search]
    if np.std(ref)<3:return unknown('No usable printed structure in the answer area.')
    # Match expected printed ink against scan ink; additional pen strokes must
    # not pull registration towards another option or lower the match quality.
    printed=(ref>40).astype('float32')
    if printed.sum()<20:return unknown('Too little printed structure to align this question.')
    distance=cv2.distanceTransform((src<=20).astype('uint8'),cv2.DIST_L2,3)
    missing=cv2.matchTemplate(np.minimum(distance,4),printed,cv2.TM_CCORR)/printed.sum()
    yy,xx=np.mgrid[-search:search+1,-search:search+1]
    cost=missing+.002*(xx*xx+yy*yy)
    _,_,location,_=cv2.minMaxLoc(cost)
    dx,dy=location[0]-search,location[1]-search
    correlation=max(0.,1.-float(missing[location[1],location[0]])/2)
    if correlation<.6 or abs(dx)==search or abs(dy)==search:
        return unknown('Local alignment is uncertain; inspect the original scan.')
    vals=[];unit=max(.6,scale*scale)
    for x,y,xx,yy in boxes:
        if min(x+dx,y+dy)<0 or xx+dx>w or yy+dy>h or xx<=x or yy<=y:
            return unknown('Answer area is outside the scan.')
        ag=a[y+dy:yy+dy,x+dx:xx+dx];bg=b[y:yy,x:xx]
        border=max(1,round(scale));kernel=np.ones((border*2+1,border*2+1),np.uint8)
        old=cv2.dilate((bg>30).astype('uint8'),kernel)>0
        added=((ag>27)&~old).astype('uint8')
        # Locate a closed checkbox in the blank master, not in the marked scan.
        contours,_=cv2.findContours((bg>30).astype('uint8'),cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
        candidates=[]
        for contour in contours:
            bx,by,bw,bh=cv2.boundingRect(contour);area=cv2.contourArea(contour)
            if bw>=5*scale and bh>=5*scale and .35<bw/bh<1.7 and area>bw*bh*.55 and bw<bg.shape[1]*.85 and bh<bg.shape[0]*.95:
                candidates.append((area,bx,by,bw,bh))
        anchor_pixels=0
        if candidates:
            _,bx,by,bw,bh=max(candidates);inset=max(1,round(2*scale))
            anchor_pixels=int(added[by+inset:by+bh-inset,bx+inset:bx+bw-inset].sum())
        _,_,stats,_=cv2.connectedComponentsWithStats(added,8)
        vals.append({'ratio':round(float(added.mean()),4),
                     'pixels':int(max(stats[1:,cv2.CC_STAT_AREA],default=0)),
                     'inside_pixels':anchor_pixels,'box_found':bool(candidates)})
    marked=[i for i,v in enumerate(vals) if v['ratio']>=.018 and v['pixels']>=7*unit and v['inside_pixels']>=3*unit]
    # A second weak interior mark may be a correction. Do not silently pick it away.
    competing=[i for i,v in enumerate(vals) if v['ratio']>=.009 and v['pixels']>=4*unit and v['inside_pixels']>=2*unit]
    if len(marked)==1 and all(i==marked[0] for i in competing):
        answer='ABCD'[marked[0]];reason='Single mark after brightness and local alignment correction; verify scan.'
    elif len(marked)>1:
        answer='?';reason='Multiple marks or correction; review the scan.'
    elif any(v['pixels']>=4*unit for v in vals):
        answer='?';reason='Faint, off-box or conflicting ink; review before scoring.'
    else:
        answer='?';reason='No reliable mark found; confirm a blank from the scan.'
    return {'answer':answer,'reason':reason,'evidence':vals,
            'local_shift':[dx,dy],'alignment':round(float(correlation),3)}

def checkbox_evidence(a,b,rect):
 h,w=a.shape;scale=w/1100; x,y,rw,rh=rect;x,y,xx,yy=int(x*w),int(y*h),int((x+rw)*w),int((y+rh)*h)
 bg=b[y:yy,x:xx];cs,_=cv2.findContours((bg>30).astype('uint8'),cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
 cand=[]
 for cc in cs:
  bx,by,bw,bh=cv2.boundingRect(cc);ar=cv2.contourArea(cc)
  if bw>=5*scale and bh>=5*scale and .3<bw/bh<1.8 and ar>bw*bh*.5 and bw<bg.shape[1]*.9 and bh<bg.shape[0]*.97:cand.append((ar,bx,by,bw,bh))
 if not cand:return None
 _,bx,by,bw,bh=max(cand);ref=bg[by:by+bh,bx:bx+bw];margin=max(4,round(7*scale))
 bx+=x;by+=y
 if bx<margin or by<margin or bx+bw+margin>w or by+bh+margin>h:return None
 src=a[by-margin:by+bh+margin,bx-margin:bx+bw+margin]
 ink=(ref>35).astype('float32');inset=max(1,round(3*scale));ink[inset:-inset,inset:-inset]=0
 dist=cv2.distanceTransform((src<25).astype('uint8'),cv2.DIST_L2,3)
 costs=cv2.matchTemplate(np.minimum(dist,3),ink,cv2.TM_CCORR)/max(1,ink.sum())
 iy,ix=np.mgrid[-margin:margin+1,-margin:margin+1];costs+=.005*(ix*ix+iy*iy)
 _,_,loc,_=cv2.minMaxLoc(costs);dx,dy=loc[0]-margin,loc[1]-margin
 cut=src[loc[1]:loc[1]+bh,loc[0]:loc[0]+bw]
 old=cv2.dilate((ref>30).astype('uint8'),np.ones((max(1,round(scale))*2+1,)*2,np.uint8))>0
 inside=np.zeros(ref.shape,bool);inset=max(1,round(2*scale));inside[inset:-inset,inset:-inset]=True
 vals=[]
 for t in (22,30,40):
  added=((cut>t)&~old&inside).astype('uint8');n,_,st,_=cv2.connectedComponentsWithStats(added,8)
  vals.append(int(max(st[1:,cv2.CC_STAT_AREA],default=0)))
 return {'pixels_by_threshold':vals,'registration_cost':round(float(costs[loc[1],loc[0]]),3),'shift':[dx,dy],'search_limit':margin}

def detect_checkbox_question(image,template,regions,prepared=None):
    prepared=prepared if prepared is not None else (ink_contrast(image),ink_contrast(template))
    legacy=detect_question_legacy(image,template,regions,prepared)
    if image.shape[:2]!=template.shape[:2] or len(regions)!=4:return {**legacy,'confidence':'review'}
    a,b=prepared;unit=max(.6,(a.shape[1]/1100)**2)
    evidence=[checkbox_evidence(a,b,r) for r in regions]
    valid=all(v and v['registration_cost']<1.25 and max(map(abs,v['shift']))<v['search_limit'] for v in evidence)
    candidates=[i for i,v in enumerate(evidence) if v and v['pixels_by_threshold'][1]>=10*unit and v['pixels_by_threshold'][2]>=5*unit and v['registration_cost']<.9]
    selected=candidates[0] if len(candidates)==1 else None
    clear=valid and selected is not None and all(v['pixels_by_threshold'][0]<5*unit for i,v in enumerate(evidence) if i!=selected)
    # The two registration methods can disagree. Such disagreements are never
    # promoted to confident answers merely because one looks stronger.
    if clear and legacy['answer'] in ('?', 'ABCD'[selected]):
        return {**legacy,'answer':'ABCD'[selected],'confidence':'strong',
                'reason':'Clear checkbox mark at three contrast levels; other options clear.',
                'checkbox_evidence':evidence}
    return {**legacy,'confidence':'review','checkbox_evidence':evidence,
            'reason':('Readers disagree; check the scan.' if clear else legacy['reason'])}

def option_evidence(scan, master, rect):
    """Inspect adjacent printed option text as well as the mapped checkbox.

    Follow short gaps in master ink, never scan handwriting, to infer the text
    extent. Registration and all thresholds are independent of reviewed labels.
    """
    height, width = scan.shape
    x, y, rw, rh = rect
    x, y, right, bottom = int(x*width), int(y*height), int((x+rw)*width), int((y+rh)*height)
    scale = width / 1100
    start = max(0, x-round(180*scale))
    columns = np.where(np.any(master[y:bottom, start:x] > 40, axis=0))[0] + start
    left = x
    for column in columns[::-1]:
        if left-column > 25*scale:
            break
        left = int(column)
    left = max(0, left-round(10*scale))
    margin = max(3, round(7*scale))
    if min(left, y) < margin or right+margin > width or bottom+margin > height:
        return None
    reference = master[y:bottom, left:right]
    source = scan[y-margin:bottom+margin, left-margin:right+margin]
    ink = (reference > 40).astype('float32')
    if ink.sum() < 15:
        return None
    distance = cv2.distanceTransform((source < 22).astype('uint8'), cv2.DIST_L2, 3)
    costs = cv2.matchTemplate(np.minimum(distance, 3), ink, cv2.TM_CCORR) / ink.sum()
    iy, ix = np.mgrid[-margin:margin+1, -margin:margin+1]
    costs += .003*(ix*ix+iy*iy)
    _, _, location, _ = cv2.minMaxLoc(costs)
    dx, dy = location
    cut = source[dy:dy+reference.shape[0], dx:dx+reference.shape[1]]
    kernel = np.ones((max(1, round(scale))*2+1,)*2, np.uint8)
    printed = cv2.dilate((reference > 25).astype('uint8'), kernel) > 0
    values = []
    for threshold in (22, 30, 40):
        added = ((cut > threshold) & ~printed).astype('uint8')
        _, _, components, _ = cv2.connectedComponentsWithStats(added, 8)
        values.append(int(max(components[1:, cv2.CC_STAT_AREA], default=0)))
    return {'v': values, 'cost': float(costs[dy, dx]), 'shift': [dx-margin, dy-margin],
            'left': left, 'limit': margin}


def detect_question(image, template, regions, prepared=None):
    """Keep option-text marks as suggestions until checked, never as final marks."""
    prepared = prepared if prepared is not None else (ink_contrast(image), ink_contrast(template))
    result = detect_checkbox_question(image, template, regions, prepared)
    if image.shape[:2] != template.shape[:2] or len(regions) != 4:
        return result
    evidence = [option_evidence(*prepared, rect) for rect in regions]
    result['option_evidence'] = evidence
    unit = max(.6, (image.shape[1] / 1100) ** 2)
    valid = all(v and v['cost'] < .6 and max(map(abs, v['shift'])) < v['limit'] for v in evidence)
    if not valid:
        return result
    competing = [v for v in evidence if v['v'][1] >= 7 * unit and v['v'][2] >= 4 * unit]
    if len(competing) > 1 and result.get('confidence') != 'strong':
        return {**result, 'answer': '?', 'confidence': 'review',
                'reason': 'Ink at multiple option positions; check for a crossed-out choice or tick tail.'}
    selected = [i for i, v in enumerate(evidence) if v['v'][1] >= 15 * unit and v['v'][2] >= 7.5 * unit]
    if len(selected) != 1 or any(v['v'][0] >= 5 * unit for i, v in enumerate(evidence) if i not in selected):
        return result
    choice = 'ABCD'[selected[0]]
    if result['answer'] not in ('?', choice):
        return {**result, 'answer': '?', 'confidence': 'review',
                'reason': 'Checkbox and surrounding option marks disagree; check for a correction.'}
    # A wider region can include a crossed-out option label or a tick tail.
    # Recover a checkbox only when this region contains no adjacent option text.
    box_only = (regions[selected[0]][0] * image.shape[1] - evidence[selected[0]]['left']) <= 15 * image.shape[1] / 1100
    if result['answer'] == '?' and box_only:
        return {**result, 'answer': choice, 'confidence': 'review',
                'reason': 'Mark recovered around a faint checkbox; verify the scan.'}
    if result['answer'] == '?':
        return {**result, 'suggested_answer': choice, 'confidence': 'review',
                'reason': 'Possible mark beside the option text. Check for crossed-out choices before accepting.'}
    return result

def detect_page(image,template,mapping,page):
    prepared=(ink_contrast(image),ink_contrast(template))
    return {int(q)-1:detect_question(image,template,m['boxes'],prepared)
            for q,m in mapping.items() if m['page']==page}

def combine_resolution_reads(first, second):
    """A second rendering may recover fine strokes, but cannot erase a conflict.

    Recovery requires strong checkbox evidence, not a text-side suggestion.
    Recovered choices stay reviewable; this is not an automatic approval rule.
    """
    result = dict(first)
    for q, extra in second.items():
        original = first.get(q)
        if original is None:
            continue
        a, b = original['answer'], extra['answer']
        evidence = {'answer': b, 'confidence': extra.get('confidence'),
                    'reason': extra.get('reason'), 'checkbox_evidence': extra.get('checkbox_evidence')}
        result[q] = {**original, 'second_resolution': evidence}
        if a != '?' and b != '?' and a != b:
            result[q].update(answer='?', confidence='review',
                             reason='Different resolutions disagree; inspect the original scan.')
        elif a == '?' and b != '?' and extra.get('confidence') == 'strong':
            # A conflicting text-side reading still needs a person to resolve it.
            if original.get('suggested_answer') not in (None, b):
                continue
            result[q].update(answer=b, confidence='review',
                             reason='Fine checkbox strokes recovered at higher resolution; verify the scan.')
    return result

def detect_page_with_retry(source_page, image, template, mapping, page, high_template):
    """Retry only pages containing exceptions, keeping one high-res page in memory."""
    first = detect_page(image, template, mapping, page)
    if high_template is None or not any(d.get('confidence') != 'strong' for d in first.values()):
        return first
    high, quality = align(raster(source_page, 3.4), high_template)
    if high is None:
        return {q: {**d, 'second_resolution': {'reason': 'Higher-resolution alignment failed.'}}
                for q, d in first.items()}
    second = detect_page(high, high_template, mapping, page)
    combined = combine_resolution_reads(first, second)
    from whole_option import supplement, blue_contrast
    planes = (blue_contrast(image), blue_contrast(template))
    combined = {q: supplement(d, image, template, mapping[str(q+1)]['boxes'], planes) for q,d in combined.items()}
    from page_refinement import refine, merge_reads
    local, registration = refine(image, template, ink_contrast)
    if local is None:
        return combined
    local_reads = detect_page(local, template, mapping, page)
    high_local, _ = refine(high, high_template, ink_contrast)
    if high_local is not None:
        local_reads = combine_resolution_reads(local_reads, detect_page(high_local, high_template, mapping, page))
    merged = merge_reads(combined, local_reads)
    from stroke_reader import stroke_evidence, recover
    stroke_pages = ((image,template),(local,template),(high,high_template))
    contrasts = [(ink_contrast(pixels),ink_contrast(ref)) for pixels,ref in stroke_pages]
    for q,d in merged.items():
        boxes = mapping[str(q+1)]['boxes']
        readings = [stroke_evidence(pixels, ref, boxes, ink_contrast, prepared=prepared)
                    for (pixels,ref),prepared in zip(stroke_pages,contrasts)]
        merged[q] = recover(d, readings)
        merged[q]['local_registration'] = registration
    return merged

def reread_data(old,detected,key,protected=()):
    """Keep saved human choices and student details when refreshing suggestions."""
    overrides=set(old.get('answer_overrides',[]))|set(protected)
    answers=[old['answers'][i] if i in overrides else detected[i]['answer'] for i in range(25)]
    return {**old,'answers':answers,'details':detected,'score':score(answers,key),
            'answer_overrides':sorted(overrides),'detected_answers':[d['answer'] for d in detected],
            'mark_reader_version':MARK_READER_VERSION,'reread_requested':False}

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
