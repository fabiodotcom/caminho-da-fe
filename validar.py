"""Compara a base nova com a atual. Sai com código 1 se a diferença for grande demais."""
import sys,json,collections
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
print('registros',len(velha),'->',len(nova),'| mantidos',f'{ps:.0%}')
if falhas:
    print('FALHA NA VALIDAÇÃO:');[print(' -',x) for x in falhas];sys.exit(1)
print('validação ok')
