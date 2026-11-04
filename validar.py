"""Compara a base nova com a atual e confere os ramais.
Saída com código 1 (a base não é publicada) se:
  - a diferença for grande demais, ou
  - houver um município depois do km 241 que não esteja classificado (ramal P, G ou comum aos dois).
"""
import sys,json,re

KM_BIFURCA=241
RAMAL_G=re.compile(r'Guaratingu|Gomeral|Potim|Pedrinhas',re.I)
RAMAL_P=re.compile(r'Pindamonhangaba|Piracuama|Pinhal|Ribeir[ãa]o Grande|Mandu',re.I)
COMUM=re.compile(r'Campos do Jordão|Aparecida',re.I)   # trechos que valem para os dois ramais

velha=json.load(open(sys.argv[1]))['hosp'];nova=json.load(open(sys.argv[2]))['hosp']

def K(x): return (x['nome'],x['municipio'],x['km_pdf'])
ka={K(x):x for x in velha};kb={K(x):x for x in nova}
ps=len(set(ka)&set(kb))/max(len(ka),1)
falhas=[]
if len(nova)<0.9*len(velha): falhas.append(f'registros caíram de {len(velha)} para {len(nova)}')
if ps<0.95: falhas.append(f'só {ps:.0%} dos registros se mantêm')
for f in ['km_inicio','preco_min','preco_max']:
    trocas=sum(1 for k in set(ka)&set(kb) if ka[k][f]!=kb[k][f])
    if trocas>0.02*len(ka): falhas.append(f'{trocas} valores de {f} mudaram')

# ramais: município depois da bifurcação que não está classificado
desconhecidos=sorted({x['municipio'] for x in nova
    if x.get('km_inicio') is not None and x['km_inicio']>KM_BIFURCA
    and not (RAMAL_G.search(x['municipio'] or '') or RAMAL_P.search(x['municipio'] or '') or COMUM.search(x['municipio'] or ''))})
if desconhecidos:
    falhas.append('municípios depois do km 241 sem ramal definido: '+', '.join(desconhecidos)+
                  ' — inclua o nome em validar.py (RAMAL_G, RAMAL_P ou COMUM) e no app (core.js, ramalDoPonto)')

print('registros',len(velha),'->',len(nova),'| mantidos',f'{ps:.0%}')
if falhas:
    print('FALHA NA VALIDAÇÃO:');[print(' -',x) for x in falhas];sys.exit(1)
print('validação ok')
