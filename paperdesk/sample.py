"""Synthetic end-to-end fixture; never presented as real student data."""
from pathlib import Path
import io
from reportlab.pdfgen import canvas
import pymupdf as fitz
import cv2
from processor import raster
W,H=595,842
KEY=list('ABCDABCDABCDABCDABCDABCDA')

def create_pdf(path,students=None):
    c=canvas.Canvas(str(path),pagesize=(W,H));mapping={};fields={}
    count=1 if students is None else len(students)
    for st in range(count):
        for page in range(2):
            c.setFont('Helvetica-Bold',19);c.drawString(42,799,'PaperDesk - SYNTHETIC TEST PAPER')
            c.setFont('Helvetica',10);c.drawString(42,775,f'Page {page+1} of 2 | Class 9 | Not an official examination')
            c.rect(27,25,541,786)
            if page==0:
                c.drawString(42,742,'Student:');c.rect(105,730,310,22)
                fields['name']={'page':0,'box':[105/W,(H-752)/H,310/W,22/H]}
                if students is not None:c.drawString(112,737,students[st])
                c.drawString(42,710,'School:');c.rect(105,698,310,22);fields['school']={'page':0,'box':[105/W,(H-720)/H,310/W,22/H]}
                if students is not None:c.drawString(112,705,'Synthetic Demonstration School')
            lo,hi=(1,11) if page==0 else (11,26)
            for j,q in enumerate(range(lo,hi)):
                col=j//8;row=j%8;x=42+col*270;y=(663 if page==0 else 718)-row*78
                c.setFont('Helvetica-Bold',11);c.drawString(x,y,f'Q{q}. Synthetic question {q}')
                c.setFont('Helvetica',9);c.drawString(x,y-15,f'Fixture row {q}: select one option.')
                boxes=[]
                for opt in range(4):
                    bx=x+opt*55;by=y-41;c.drawString(bx,by+2,'ABCD'[opt]);c.rect(bx+15,by,11,11)
                    # Include the area where a tick stroke leaves the square.
                    boxes.append([(bx+12)/W,(H-(by+17))/H,25/W,21/H])
                    if students is not None:
                        correct='ABCD'.index(KEY[q-1]); chosen=correct
                        if st==1 and q%4==0:chosen=(correct+1)%4
                        if st==2 and q==5:continue
                        if chosen==opt or (st==2 and q==20 and opt==(correct+1)%4):
                            c.setStrokeColorRGB(.05,.1,.5);c.setLineWidth(2);c.line(bx+17,by+5,bx+21,by+1);c.line(bx+21,by+1,bx+31,by+14);c.setStrokeColorRGB(0,0,0);c.setLineWidth(1)
                mapping[str(q)]={'page':page,'boxes':boxes}
            c.showPage()
    c.save();return {'key':KEY,'mapping':mapping,'fields':fields}
