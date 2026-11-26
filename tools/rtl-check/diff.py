from PIL import Image, ImageChops
import os, sys
def bb(a,b):
    A=Image.open(a).convert('RGB'); B=Image.open(b).convert('RGB')
    if A.size!=B.size: return 'size'
    return ImageChops.difference(A,B).getbbox()
real=0
for f in sorted(os.listdir('before')):
    x=bb('before/'+f,'after/'+f); y=bb('before2/'+f,'after/'+f)
    if x and y:
        real+=1; print('CHANGED', f, x, y)
print('pages with a real change:', real, 'of', len(os.listdir('before')))
