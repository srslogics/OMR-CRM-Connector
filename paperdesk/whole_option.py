"""Supplementary blue-pen reading across option rows, with conflict vetoes.

This is not a handwriting classifier or an automatic approval policy. Black ink
is still handled by the registered grayscale reader; its conflicts take priority.
"""
import cv2
import numpy as np


def blue_contrast(image):
    b,g,r=cv2.split(image.astype('float32'))
    plane=np.minimum(b-r,b-g)
    return plane-cv2.GaussianBlur(plane,(0,0),max(1,15*image.shape[1]/1100))


def supplement(result, image, template, regions, planes=None):
    if image.shape!=template.shape or len(regions)!=4:return result
    scan,master=planes if planes is not None else (blue_contrast(image),blue_contrast(template))
    h,w=scan.shape;unit=max(.6,(w/1100)**2);evidence=[]
    for x,y,rw,rh in regions:
        same=[box for box in regions if abs(box[1]+box[3]/2-y-rh/2)<rh*.6]
        left=.5 if x>=.5 else .05
        if len(same)>1:left=max(left,x-.14)
        x0,x1=max(0,int(left*w)),min(w,int((x+rw+.015)*w))
        y0,y1=max(0,int(y*h)),min(h,int((y+rh)*h))
        a,b=scan[y0:y1,x0:x1],master[y0:y1,x0:x1]
        values=[]
        for threshold in (8,12,18):
            # Avoid treating coloured print present in the master as a pen mark.
            old=cv2.dilate((b>threshold/2).astype('uint8'),np.ones((3,3),np.uint8))>0
            mask=((a>threshold)&~old).astype('uint8')
            if not mask.size:values.append(0);continue
            _,_,stats,_=cv2.connectedComponentsWithStats(mask,8)
            values.append(int(max(stats[1:,4],default=0)))
        evidence.append(values)
    out={**result,'whole_option_color':evidence}
    candidates=[i for i,v in enumerate(evidence) if v[1]>=12*unit and v[2]>=6*unit]
    if len(candidates)!=1:return out
    selected=candidates[0];choice='ABCD'[selected]
    if any(v[0]>=5*unit for i,v in enumerate(evidence) if i!=selected):return out
    # A blue tick must not hide black corrections, alternate marks or disagreement.
    reason=result.get('reason','').lower()
    if any(word in reason for word in ('multiple','disagree','conflict','correction')):return out
    for reading in (result,result.get('second_resolution',{})):
        if reading.get('answer','?') not in ('?',choice):return out
        if reading.get('suggested_answer') not in (None,choice):return out
        for i,v in enumerate(reading.get('checkbox_evidence',[])):
            scale=4 if reading is not result else 1
            if i!=selected and v and v['pixels_by_threshold'][1]>=7*unit*scale:return out
    if result.get('answer')=='?':
        out.update(answer=choice,confidence='review',reason='Blue pen stroke recovered across the option row; retained for audit.')
    return out
