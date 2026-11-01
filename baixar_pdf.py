"""Descobre o PDF do ramal principal no site da AACF e baixa se houver edição nova.
Saída (GITHUB_OUTPUT): mudou=true|false, arquivo=<caminho>, edicao=<n>
"""
import sys,os,re,json,urllib.request
PAGINA='https://caminhodafe.com.br/ptbr/pousadas/'
SAIDA=sys.argv[1] if len(sys.argv)>1 else 'fonte.json'
def out(k,v):
    p=os.environ.get('GITHUB_OUTPUT')
    if p: open(p,'a').write(f'{k}={v}\n')
    print(f'{k}={v}')
html=urllib.request.urlopen(PAGINA,timeout=30).read().decode('utf-8','ignore')
# links de PDF do ramal principal (o site publica uma planilha por ramal)
links=re.findall(r'https://caminhodafe\.com\.br/ptbr/wp-content/uploads/[^"\s<>]+\.pdf',html,re.I)
alvo=[l for l in links if re.search(r'Ramal-Principal|Aguas-da-Prata',l,re.I)]
if not alvo: raise SystemExit('PDF do ramal principal não encontrado na página')
url=alvo[0]
m=re.search(r'Edi[çc][ãa]o[-_ ]([\d.]+)',url,re.I);edicao=m.group(1) if m else ''
atual=json.load(open(SAIDA)) if os.path.exists(SAIDA) else {}
if atual.get('url')==url:
    out('mudou','false');out('edicao',edicao);raise SystemExit
arq='ramal-principal.pdf'
urllib.request.urlretrieve(url,arq)
json.dump({'url':url,'edicao':edicao},open('fonte.pendente.json','w'),ensure_ascii=False,indent=1)  # só vira fonte.json após publicar
out('mudou','true');out('arquivo',arq);out('edicao',edicao)
