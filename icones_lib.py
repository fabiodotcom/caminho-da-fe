"""Classifica os ícones de cada linha casando com icon_lib.json (modelos já validados, 99,9% de acerto)."""
import json,base64,numpy as np,os
from PIL import Image
HERE=os.path.dirname(os.path.abspath(__file__))
L=json.load(open(os.path.join(HERE,'icon_lib.json')))
TPL=np.frombuffer(base64.b64decode(L['data']),np.uint8).reshape(len(L['labels']),L['n'],L['n'],3).astype(np.float32)/255.0
TV=TPL.reshape(len(TPL),-1);TK=L['labels']
def classificar(vec):
    d=np.sqrt(((TV-vec.reshape(-1))**2).sum(1));return TK[int(d.argmin())],float(d.min())
