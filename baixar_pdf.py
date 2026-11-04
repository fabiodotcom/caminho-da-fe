"""Verifica no site da AACF se há uma edição nova do PDF do ramal principal.
Saída (GITHUB_OUTPUT): mudou=true|false, arquivo=<caminho>, edicao=<n>.
Se o site não responder ou o link não for encontrado, registra um aviso e mantém a lista atual (sem falhar a rotina)."""
import sys,os,re,json,time,urllib.request
PAGINA=os.environ.get('PAGINA_TESTE','https://caminhodafe.com.br/ptbr/pousadas/')
SAIDA=sys.argv[1] if len(sys.argv)>1 else 'fonte.json'
CABECALHOS={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
            'Accept':'text/html,application/pdf;q=0.9,*/*;q=0.8','Accept-Language':'pt-BR,pt;q=0.9'}
def out(k,v):
    p=os.environ.get('GITHUB_OUTPUT')
    if p: open(p,'a').write(f'{k}={v}\n')
    print(f'{k}={v}')
def baixar(url,tentativas=3):
    ultimo=None
    for i in range(tentativas):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=CABECALHOS),timeout=60) as r:
                return r.read()
        except Exception as e:
            ultimo=e; print(f'tentativa {i+1} falhou: {e}'); time.sleep(5*(i+1))
    raise ultimo
def aviso(msg):
    print(f'::warning title=Base de hospedagens::{msg}')
    out('mudou','false'); out('edicao','')
try:
    html=baixar(PAGINA).decode('utf-8','ignore')
    links=set(re.findall(r'https://caminhodafe\.com\.br/ptbr/wp-content/uploads/[^"\s<>\']+\.pdf',html,re.I))
    alvo=sorted(l for l in links if re.search(r'Ramal-Principal|Aguas-da-Prata',l,re.I))
    if not alvo: raise RuntimeError('link do PDF do ramal principal não encontrado na página (o site pode ter mudado)')
    url=alvo[0]
    m=re.search(r'Edi[çc][ãa]o[-_ ](\d+(?:\.\d+)*)',url,re.I);edicao=m.group(1) if m else ''
    atual=json.load(open(SAIDA)) if os.path.exists(SAIDA) else {}
    if atual.get('url')==url:
        out('mudou','false');out('edicao',edicao);sys.exit(0)
    dados=baixar(url)
    if not dados.startswith(b'%PDF'): raise RuntimeError('o endereço não devolveu um PDF')
    open('ramal-principal.pdf','wb').write(dados)
    json.dump({'url':url,'edicao':edicao},open('fonte.pendente.json','w'),ensure_ascii=False,indent=1)  # só vira fonte.json após publicar
    out('mudou','true');out('arquivo','ramal-principal.pdf');out('edicao',edicao)
except SystemExit:
    raise
except Exception as e:
    aviso(f'Verificação não concluída ({e}). A lista atual foi mantida; a próxima execução tenta de novo.')
    sys.exit(0)
