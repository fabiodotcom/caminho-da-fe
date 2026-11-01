"""Gera data/base-ramal-principal.json a partir de um PDF de ramal.
Uso: PDF_IN=arquivo.pdf OUT=saida.json python gerar_base.py
"""
import os,sys,json,re,hashlib,collections
import numpy as np
S=2.0;TOTAL=317.0
PDF=os.environ['PDF_IN'];OUT=os.environ['OUT']
import pdfplumber
from PIL import Image
import parse_lib as PL
from icones_lib import classificar,TPL
os.environ['PDF_IN']=PDF
raw=PL.main()
# ---- ícones: miniatura de cada ícone pequeno, classificada pela biblioteca ----
def thumb(img,bb):
    x0,y0,x1,y1=[int(round(v*S)) for v in bb]
    return np.asarray(img.crop((x0,y0,x1,y1)).convert('RGB').resize((20,20),Image.LANCZOS),np.float32)/255.0
icon_labels={}
with pdfplumber.open(PDF) as pdf:
    byp=collections.defaultdict(list)
    for i,e in enumerate(raw): byp[e['pagina']-1].append(i)
    for pi,idxs in byp.items():
        p=pdf.pages[pi];img=p.to_image(resolution=72*S).original
        small=[im for im in p.images if 6<=im['x1']-im['x0']<=40 and 6<=im['bottom']-im['top']<=40]
        for i in idxs:
            e=raw[i];b0,b1=e['_band'];o0,o1=e['_obsx'];labs=[]
            for im in small:
                if o0-1<=im['x0']<=o1 and b0-2<=im['top']<=b1:
                    lab,dist=classificar(thumb(img,(im['x0'],im['top'],im['x1'],im['bottom'])))
                    labs.append(lab)
            icon_labels[i]=labs
print('registros',len(raw),'com ícones',sum(1 for v in icon_labels.values() if v))

# ---- normalização ----
from normaliza import montar
out=montar(raw,icon_labels)
import re as _r
with pdfplumber.open(PDF) as P:
    t=P.pages[0].extract_text() or ''
ed=_r.search(r'EDI[ÇC][ÃA]O\s*([\d.]+)',t,_r.I);at=_r.search(r'Atualizado em:?\s*(\d\d/\d\d/\d{4})',t,_r.I)
doc={'meta':{'edicao':ed.group(1) if ed else '','atualizado':at.group(1) if at else '','arquivo':os.path.basename(PDF)},'hosp':out}
json.dump(doc,open(OUT,'w'),ensure_ascii=False,indent=1)
print('gravado',OUT,len(out),doc['meta'])
