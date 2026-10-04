"""Read long checkmark strokes that extend outside mapped answer boxes.

The low turning point anchors a tick to its option. Its rising tail must not
vote for the option above it. This supplements, never replaces, the box reader.
"""
import cv2
import numpy as np


def competing_mark_veto(detail, width):
    """A weak second tick can survive at both resolutions below the strong cutoff."""
    if detail.get('answer') not in ('A','B','C','D'):
        return detail
    local_reason = detail.get('local_read',{}).get('reason','').lower()
    if not any(word in local_reason for word in ('multiple','correction')):
        return detail
    primary = detail.get('checkbox_evidence',[])
    secondary = detail.get('second_resolution',{}).get('checkbox_evidence',[])
    options = detail.get('option_evidence',[])
    if not all(len(items)==4 for items in (primary,secondary,options)):
        return detail
    unit = max(.6,(width/1100)**2)
    for i,(a,b,o) in enumerate(zip(primary,secondary,options)):
        if 'ABCD'[i] == detail['answer'] or not all((a,b,o)):
            continue
        if (a['registration_cost'] < .9 and b['registration_cost'] < .9
            and a['pixels_by_threshold'][0] >= 3*unit
            and b['pixels_by_threshold'][1] >= 16*unit
            and b['pixels_by_threshold'][2] >= 10*unit
            and o['cost'] < .6 and o['v'][1] >= 7*unit and o['v'][2] >= 4*unit):
            return {**detail,'answer':'?','confidence':'review',
                    'reason':'Multiple marks or correction supported at two resolutions and option text.'}
    return detail


def stroke_evidence(image, template, boxes, contrast, threshold=30, prepared=None):
    if image.shape != template.shape or len(boxes) != 4:
        return {'answer':'?', 'marks':[]}
    a,b=prepared if prepared is not None else (contrast(image),contrast(template))
    h,w=a.shape;scale=w/1100
    left=max(0,int(min(x[0] for x in boxes)*w)-round(12*scale))
    right=min(w,int(max(x[0]+x[2] for x in boxes)*w)+round(100*scale))
    top=max(0,int(min(x[1] for x in boxes)*h)-round(35*scale))
    bottom=min(h,int(max(x[1]+x[3] for x in boxes)*h)+round(12*scale))
    if right<=left or bottom<=top:return {'answer':'?', 'marks':[]}
    kernel=np.ones((max(1,round(scale))*2+1,)*2,np.uint8)
    printed=cv2.dilate((b[top:bottom,left:right]>25).astype('uint8'),kernel)>0
    mask=((a[top:bottom,left:right]>threshold)&~printed).astype('uint8')
    joined=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,kernel)
    _,components,stats,_=cv2.connectedComponentsWithStats(joined,8)
    marks=[]
    for i,(x,y,ww,hh,area) in enumerate(stats[1:],1):
        if ww<10*scale or hh<8*scale or area<15*scale*scale or ww>120*scale:continue
        yy,xx=np.where((components==i)&(mask>0))
        if len(xx)<12*scale*scale:continue
        floor=yy.max();base=xx[yy>=floor-max(1,round(2*scale))]
        bx,by=float(np.median(base)),float(floor)
        root=(bx+left,by+top)
        choices=[j for j,(rx,ry,rw,rh) in enumerate(boxes)
                 if rx*w-8*scale<root[0]<(rx+rw)*w+8*scale
                 and ry*h-3*scale<root[1]<(ry+rh)*h+6*scale]
        if len(choices)!=1 or xx.max()-bx<=7*scale:continue
        if np.mean(yy[xx>bx+7*scale])>=by-3*scale:continue
        option=choices[0]
        long=ww>=max(20*scale,boxes[option][2]*w) and area/(ww*hh)<.55
        marks.append({'option':option,'root':list(root),'width':int(ww),'height':int(hh),'long':bool(long)})
    choices={m['option'] for m in marks}
    selected=[m['option'] for m in marks if m['long']]
    answer='ABCD'[selected[0]] if len(choices)==1 and selected else '?'
    return {'answer':answer,'marks':marks}


def recover(before, readings):
    """Require agreement across resolutions/registration, with conflict vetoes."""
    if not readings:return before
    answers=[r['answer'] for r in readings]
    out={**before,'stroke_reads':readings}
    conflicts = [len({m['option'] for m in r.get('marks',[])}) > 1
                 and any(m['long'] for m in r.get('marks',[])) for r in readings]
    if sum(conflicts) >= 2:
        return {**out,'answer':'?','confidence':'review',
                'reason':'Separate checkmark strokes at multiple options; inspect the correction.'}
    if '?' in answers or len(set(answers))!=1:return out
    choice=answers[0]
    if before['answer'] not in ('?',choice):
        return {**out,'answer':'?','confidence':'review',
                'reason':'Checkbox and checkmark-stroke readings disagree.'}
    if before.get('suggested_answer') not in (None,choice):return out
    # Multiple interior marks can be a correction even if only one long tick survives.
    for read,scale in ((before,1),(before.get('second_resolution',{}),4)):
        for i,e in enumerate(read.get('checkbox_evidence',[])):
            if e and 'ABCD'[i]!=choice and e['pixels_by_threshold'][1]>=10*scale:return out
    if before['answer']=='?':
        out.update(answer=choice,confidence='review',
                   reason='Long tick recovered by its turning point at two resolutions and local alignment.')
    return out
