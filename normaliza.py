import re,hashlib,collections
TOTAL=317.0
def clean_city(c,pagina,ramal):
    c=re.sub(r'\s*trilha\b','',c).replace("'",'').strip()
    c=re.sub(r'\(\s*Município de\s*','(',c); c=re.sub(r'\s*/\s*',r'/',c)
    c=re.sub(r'\(\s+','(',c).replace(' )',')')
    if c.startswith('Aparecida'): return 'Aparecida','SP'
    if c.startswith('(Pindamonhangaba'): return 'Pindamonhangaba','SP'
    if c.startswith('(Guaratinguetá'): return 'Gomeral (Guaratinguetá)','SP'
    m=re.match(r'^(.*?)\s*\((.*?)/(\w\w)\)$',c)
    if m: loc=m.group(1).strip(); return (f'{loc} ({m.group(2)})' if loc else m.group(2)), m.group(3)
    m=re.match(r'^(.*)/(\w\w)$',c)
    if m: return m.group(1).strip(),m.group(2)
    return c,''
def tipo_cat(e):
    obs=' '.join(e['obs']).upper(); n=e['nome'].lower()
    if e['precos'] or e['preco_texto']: t='hospedagem'
    elif re.search(r'PONTO DE APOIO|APOIO|MASSAG',obs): t='apoio'
    elif re.search(r'\b(QT|QTO|APTO|SGL|SLG|DBL|TPL|BELICHE)\b',obs): t='hospedagem'
    elif re.search(r'pousada|hotel|hostel|hospedaria|chalé|chale|refúgio|camping|rancho dos|apartamento|casa de vó|flat',n): t='hospedagem'
    else: t='apoio'
    cat='Outro'
    for k,v in [('hostel','Hostel'),('hotel','Hotel'),('pousada','Pousada'),('hospedaria','Hospedaria'),('chalé','Chalé'),('chalés','Chalé'),('camping','Camping'),('apartamento','Apartamento'),('casa do peregrino','Casa do Peregrino'),('refúgio','Refúgio'),('rancho','Rancho'),('recanto','Recanto'),('casa','Casa')]:
        if k in n: cat=v;break
    if t=='apoio':
        cat='Ponto de apoio'
        if re.search(r'bike|bicicl',n+obs.lower()): cat='Apoio para bike'
        if re.search(r'massag',n+obs.lower()): cat='Massagem'
    return t,cat
TIPOIC={'t:pousada':'Pousada','t:hotel':'Hotel','t:hostel':'Hostel','t:hospedaria_rural':'Hospedaria rural','t:casa_familia':'Casa de família','t:casa_peregrino':'Casa do Peregrino','t:hotel_fazenda':'Hotel fazenda','t:mosteiro':'Mosteiro','t:temporada':'Casa de temporada'}
def amen(e,ri,tipo):
    a=set();tipo_ac=''
    if e.get('credencial'): a.add('credencial')
    for k in ICONLAB.get(ri,[]):
        if k in TIPOIC: tipo_ac=TIPOIC[k];continue
        if k.startswith('-') or k=='telefone': continue
        a.add(k)
    txt=' '.join(e['obs']).upper()+' '+' '.join(e['extras']).upper()
    if re.search(r'CAF[ÉE] DA MANH',txt) and re.search(r'INCLUSO|INCLUI',txt): a.add('cafe')
    if re.search(r'JANTAR|ALMO[ÇC]O|REFEI',txt): a.add('refeicoes')
    if tipo=='hospedagem':
        o=re.sub(r'WC\s*/?\s*CL','WCCL',' '.join(e['obs']).upper())
        tk=set(re.split(r'[^A-Z]+',o))
        if 'AC' in tk: a.add('ar_condicionado')
        if tk&{'VT','VS'}: a.add('ventilador')
        if 'TV' in tk: a.add('tv')
        if 'FB' in tk: a.add('frigobar')
        if 'WCCL' in tk: a.add('banheiro_coletivo')
        if 'APTO' in tk or ('WC' in tk and 'WCCL' not in tk): a.add('banheiro_privativo')
        if tk&{'SGL','SLG'}: a.add('quarto_individual')
        if 'DBL' in tk: a.add('quarto_duplo')
        if tk&{'TPL','TLP'}: a.add('quarto_triplo')
        if 'BELICHE' in tk: a.add('beliche')
    return sorted(a),tipo_ac

def montar(raw,ICONLAB_IN):
    global ICONLAB
    ICONLAB=ICONLAB_IN
    out=[];seen=collections.Counter()
    for ri,e in enumerate(raw):
        if not e['nome']: continue
        rev=[]
        mun,uf=clean_city(e['cidade_raw'],e['pagina'],e['ramal'])
        km=e['km_pdf'];dist=e['dist']
        ramal=e['ramal']
        if mun.startswith('Águas da Prata'):
            kini=(round(dist,2) if dist is not None else (round(TOTAL-km,2) if km is not None else None)); kpdf=km if km is not None else None
        elif mun=='Aparecida':
            base=dist if dist is not None else km
            kini=round(TOTAL-base,2) if base is not None else None; kpdf=base
        else:
            kpdf=km
            kini=round(TOTAL-km,2) if km is not None else None
        fora=dist if (dist is not None and not mun.startswith(('Águas da Prata','Aparecida'))) else None
        if mun.startswith('Aparecida'): fora=None
        if re.search(r'fora da trilha|fora da\b',e['km_raw']) is None and fora is not None and fora<=0.3 and not re.search(r'fora',e['km_raw']): fora=None
        t,cat=tipo_cat(e)
        if kini is None: rev.append('Quilometragem não informada no PDF (fora da trilha / consultar)')
        hh=[x for x in e['heranca'] if not (x.startswith('cidade') and e['col'] in ('L','R'))]
        if hh: rev.append('; '.join(hh)+' — confirmar')
        pr=e['precos']
        pmin=min(pr) if pr else None; pmax=max(pr) if len(pr)>1 else None
        if re.search(r'Individual|Duplo|Triplo',e['preco_texto']):
            rev.append('Preço por tipo de quarto (individual/duplo/triplo) — ver texto original'); pmin=pr[0] if pr else None; pmax=None
        elif len(pr)>2: rev.append('Mais de dois valores de diária — conferir'); 
        if t=='hospedagem' and not pr: rev.append('Preço não informado no PDF')
        pt=e['preco_texto']
        apartir=bool(re.search(r'a partir',pt,re.I))
        phones=[];nums=set()
        for ph in e['telefones']:
            if ph['num'] in nums: continue
            nums.add(ph['num']); d=re.sub(r'\D','',ph['num'])
            ok=len(d) in (10,11)
            wa=bool(ph['whatsapp'] and ph['movel'] and ok)
            phones.append(dict(numero=ph['num'],whatsapp=wa,movel=ph['movel']))
        if not phones: rev.append('Telefone não informado')
        if t=='hospedagem' and not e['endereco']: rev.append('Endereço não identificado')
        if e['nome'] and len(e['nome'])<4: rev.append('Nome curto — conferir')
        obs=' '.join(e['obs']).strip()
        if 'CREDENCIAL' in obs:
            e['credencial']=True;obs=re.sub(r'\s*CREDENCIAL\s*',' ',obs).strip()
        ident=f"{e['nome']}|{mun}|{kpdf}|{ramal or ''}"
        seen[ident]+=1
        rid='h'+hashlib.sha1((ident+str(seen[ident])).encode()).hexdigest()[:10]
        out.append(dict(id=rid,nome=e['nome'],municipio=mun,uf=uf,tipo=t,categoria=cat,km_pdf=kpdf,ramal=ramal or '',km_inicio=kini,fora_trilha_km=fora,
          preco_min=pmin,preco_max=pmax,preco_apartir=apartir,preco_texto=pt,incluso=' | '.join(e['extras']),telefones=phones,contato=' / '.join(dict.fromkeys(e['contato'])),
          email=', '.join(dict.fromkeys(e['emails'])),site=', '.join(e['sites']),instagram=', '.join(e['social']),endereco=re.sub(r'\s+',' ',e['endereco']).strip(),
          observacoes=obs,credencial=bool(e['credencial']),pagina_pdf=e['pagina'],revisar=rev,origem='pdf_ed19',comodidades=amen(e,ri,t)[0],tipo_acomodacao=amen(e,ri,t)[1]))

    return out
