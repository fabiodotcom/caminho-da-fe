import pdfplumber,glob,re,json,collections,sys
import os
F=os.environ['PDF_IN']
S=2.0
STREET=re.compile(r'^(Rua|R\.? |Av\.? |Avenida|Rod\b|Rod\.|Rodovia|Estrada|Estr\.?|Praça|Pç|Trav|Travessa|Travessia|Alameda|Largo|Sítio|Sito |Chácara|Bairro|Zona Rural|Cel\.|Cerca|Acesso|Lavapés|MG|Trevo|Beco|Estação|Na Rua|Pç\.)',re.I)
PH=re.compile(r'\(?\b(\d{2})\)?\s?(9?\.?\d{4})\s?-?\s?(\d{4})\b')
EMAIL=re.compile(r'[\w.\-+]+@[\w\-]+(?:\.[\w\-]+)*(?:\.[a-z]{2,})?',re.I)
def green(img,bb):
    x0,y0,x1,y1=[int(v*S) for v in bb]
    c=img.crop((x0,y0,x1+1,y1+1)).convert('RGB'); px=list(c.getdata())
    if not px: return 0
    return sum(1 for r,g,b in px if g>140 and r<120 and b<150 and g-r>70)/len(px)
def lines(words,tol=3):
    ws=sorted(words,key=lambda w:(w['top'],w['x0'])); out=[];cur=[]
    for w in ws:
        if cur and abs(w['top']-cur[0]['top'])>tol: out.append(cur);cur=[]
        cur.append(w)
    if cur: out.append(cur)
    return [(l[0]['top'],' '.join(w['text'] for w in sorted(l,key=lambda w:w['x0']))) for l in out]
def money(s): return [float(m.replace('.','').replace(',','.')) for m in re.findall(r'R\$\s?(\d{1,3}(?:\.\d{3})*,\d{2}|\d+)',s)]
def isyel(r):
    c=r.get('non_stroking_color'); return isinstance(c,(tuple,list)) and len(c)==3 and tuple(round(x,2) for x in c)==(1.0,1.0,0.0)
def hseps(p,x0,x1):
    ys=[]
    for r in p.rects+p.lines:
        h=r.get('height',0)
        if h<=1.6 and r['x0']<=x0+4 and r['x1']>=x1-4: ys.append(r['top'])
    return sorted(set(round(y,1) for y in ys))
def cell_text(p,words,x0,x1,seps,y):
    # text of the cell (between separators) containing y
    lo=max([s for s in seps if s<=y+0.5],default=0); hi=min([s for s in seps if s>y+0.5],default=p.height)
    ws=[w for w in words if w['x0']>=x0-1 and w['x1']<=x1+1 and lo-0.5<=w['top']<hi-0.5]
    return lines(ws)
def kmparse(txtlines):
    T=' '.join(t for _,t in txtlines)
    km=None;dist=None;fora=False
    for m in re.finditer(r'(\d[\d.]*,?\d*)\s*(km|Km|mt|m)\b(?!\w)',T):
        v=float(m.group(1).replace('.','').replace(',','.')) if m.group(2).lower()!='km' else float(m.group(1).replace(',','.'))
        if m.group(2).lower()!='km': v=v/1000
        if dist is None: dist=v
    T2=re.sub(r'(\d[\d.]*,?\d*)\s*(km|Km|mt|m)\b','',T)
    m=re.search(r'(?<![\d,.])(\d{1,3}(?:,\d{1,2})?)(?![\d,])\s*([PG])?\b',T2)
    ramal=None
    if m:
        km=float(m.group(1).replace(',','.')); ramal=m.group(2)
    return km,dist,ramal,T

def chain(band,H,layoutA):
    lo=H['pous'][0]-1; hi=H['pous'][1] if not layoutA else 305
    lim=H['sx'][1]+1
    acc=[];used=set()
    rows=collections.defaultdict(list)
    for w in band: rows[round(w['top']/2.5)].append(w)
    # merge neighbouring buckets
    keys=sorted(rows)
    for k in keys:
        ws=sorted(rows[k]+rows.get(k+1,[])*0,key=lambda w:w['x0'])
        last=None
        for w in ws:
            if lo<=w['x0']<hi:
                acc.append(w);used.add(id(w));last=w
            elif last is not None and w['x0']-last['x1']<6.5 and w['x1']<=lim and not re.match(r'^\(?\d{2}\)?\d*-?\d*$',w['text']):
                acc.append(w);used.add(id(w));last=w
            else:
                last=None if (last is not None and w['x0']-last['x1']>=6.5) else last
    return acc,used
def parse_page(pi,p,pageimg,state):
    words=p.extract_words(x_tolerance=1.6,y_tolerance=2,keep_blank_chars=False)
    layoutB=any(w['text']=='Cidade/Bairro' for w in words)
    yel=[r for r in p.rects if isyel(r) and r['height']<=30]
    if layoutB:
        yel=[r for r in yel if r['width']<200 and r['x1']-r['x0']>40]
    else:
        yel=[r for r in yel if abs(r['x0']-186)<3 and r['width']<260]
    # group into boxes
    boxes=[]
    for r in sorted(yel,key=lambda r:(round(r['x0']/30),r['top'])):
        if boxes and abs(boxes[-1]['x0']-r['x0'])<4 and r['top']-boxes[-1]['bottom']<=3:
            boxes[-1]['bottom']=r['bottom'];boxes[-1]['x1']=max(boxes[-1]['x1'],r['x1'])
        else: boxes.append(dict(x0=r['x0'],x1=r['x1'],top=r['top'],bottom=r['bottom']))
    if layoutB:
        halves={'L':dict(city=(37,100),pous=(100,187),obs=(187,304),sx=(37,304)),'R':dict(city=(304,369),pous=(369,470),obs=(470,558),sx=(304,558))}
    else:
        halves={'A':dict(city=(37,134),km=(134,187),pous=(187,305),tel=(305,409),obs=(409,558),sx=(37,558))}
    ents=[]
    for hk,H in halves.items():
        bs=sorted([b for b in boxes if (hk=='A' or (hk=='L')==(b['x0']<250))],key=lambda b:b['top'])
        # table bottom: last horizontal separator spanning the half
        sx0,sx1=H['sx']
        seps_all=hseps(p,sx0,sx1)
        cseps=hseps(p,*H['city']); 
        kseps=hseps(p,*H['km']) if 'km' in H else cseps
        for i,b in enumerate(bs):
            top=b['top']-0.5
            nxt=bs[i+1]['top']-0.5 if i+1<len(bs) else None
            if nxt is None:
                # stop at next spanning separator after last word? use page bottom limited by seps after top+14 whose following gap has no words
                cand=[s for s in seps_all if s>b['bottom']+8]
                nxt=p.height
                # cut at DICA / ATENÇÃO full-width texts
                cut=[w['top'] for w in words if w['top']>b['bottom'] and w['x0']>=sx0 and re.match(r'(DICA|ATENÇÃO|Atenção|Entrada|Cidade|Atenção|Retirada)',w['text'])]
                if cut: nxt=min(nxt,min(cut)-0.5)
            band=[w for w in words if top<=w['top']<nxt]
            ents.append((hk,H,b,top,nxt,band,cseps,kseps))
    res=[]
    imgs=[]
    for im in p.images:
        w=im['x1']-im['x0'];h=im['bottom']-im['top']
        if 6<=w<=24 and 6<=h<=24:
            if green(pageimg,(im['x0'],im['top'],im['x1'],im['bottom']))>0.25: imgs.append(im)
    for hk,H,b,top,nxt,band,cseps,kseps in ents:
        pous,used=chain(band,H,hk=='A')
        # name: words in yellow box
        nw=[w for w in pous if b['top']-1<=w['top']<=b['bottom']-1 and w['x0']>=b['x0']-1]
        if hk in('L','R'):
            nw=[w for w in band if b['top']-1<=w['top']<=b['bottom']-1 and w['x0']>=b['x0']-1 and w['x1']<=b['x1']+1]
        name=' '.join(w['text'] for w in sorted(nw,key=lambda w:(round(w['top']),w['x0'])))
        under=[w for w in pous if w['top']>b['bottom']-1]
        # layout A tel
        if hk=='A':
            telw=[w for w in band if id(w) not in used and H['tel'][0]-1<=w['x0'] and w['x1']<=H['tel'][1]+1]
            tl=lines(telw)
            icons=[im for im in imgs if H['tel'][0]<=im['x0']<=H['tel'][1] and top-2<=im['top']<=nxt]
            obsw=[w for w in band if id(w) not in used and H['obs'][0]-1<=w['x0']]
        else:
            tl=[(t,s) for t,s in lines(under) if PH.search(s)]
            icons=[im for im in imgs if H['pous'][1]-34<=im['x0']<=H['pous'][1]+3 and top-2<=im['top']<=nxt]
            obsw=[w for w in band if id(w) not in used and H['obs'][0]-1<=w['x0'] and w['x1']<=H['obs'][1]+1]
        phones=[];contact=[];cred=False
        for t,s in tl:
            ms=list(PH.finditer(s))
            rest=PH.sub('',s)
            if 'CREDENCIAL' in rest: cred=True
            nm=re.sub(r'CREDENCIAL','',rest).strip(' ()-')
            if nm and re.search(r'[A-Za-zÀ-ÿ]{3}',nm): contact.append(nm)
            for m in ms:
                ddd,a,c=m.group(1),m.group(2).replace('.',''),m.group(3)
                num=f'({ddd}) {a}-{c}'
                wa=any(abs((im['top']+im['bottom'])/2-(t+4))<=6 for im in icons)
                phones.append(dict(num=num,whatsapp=wa,movel=a.startswith('9') and len(a)==5))
        # whatsapp ambiguity: icon w/o phone line match -> mark mobile ones if only one phone line
        if not any(ph['whatsapp'] for ph in phones) and icons and phones:
            mob=[ph for ph in phones if ph['movel']]
            if len(mob)==1: mob[0]['whatsapp']=True; 
        if not phones:
            ia=[im for im in imgs if top-2<=im['top']<=nxt and H['pous'][0]-2<=im['x0']<=H['sx'][1]]
            for t,s_ in lines(pous):
                for m in PH.finditer(s_):
                    a=m.group(2).replace('.','')
                    wa=any(abs((im['top']+im['bottom'])/2-(t+4))<=6 for im in ia)
                    phones.append(dict(num=f'({m.group(1)}) {a}-{m.group(3)}',whatsapp=wa,movel=a.startswith('9') and len(a)==5))
        # under-name lines
        ul=lines([w for w in under if not (hk in('L','R') and PH.search(w['text']) and False)])
        if hk in('L','R'): ul=[(t,s) for t,s in ul if not PH.search(s) or money(s)]
        price_lines=[];extras=[];email=[];web=[];addr=[];social=[];other=[]
        zone=False;inaddr=False
        for t,s in ul:
            s2=s.strip()
            if not s2: continue
            if EMAIL.search(s2) and '@' in s2 and not s2.startswith('@'):
                for m in EMAIL.findall(s2): email.append(m)
                zone=False; continue
            if re.search(r'www\.|\.com\.br|\.com$',s2) and not STREET.match(s2):
                web.append(s2); zone=False; continue
            if re.search(r'diária|diaria|^Individual|^Duplo|^Triplo|Suites Individuais|a partir de',s2,re.I) and not re.search(r'jantar|almoço|refeiç',s2,re.I):
                zone=True; price_lines.append(s2); continue
            if zone and re.match(r'^(a |á |ou |Ou )?R\$\s?\d',s2):
                price_lines.append(s2); continue
            if zone and re.match(r'^(Duplo|Triplo|Individual|Suites|Preços|Valores|sem refe|com jantar|Consultar|a )',s2,re.I) :
                price_lines.append(s2); continue
            if re.match(r'^(Incluso|Inclui|Café|Cafe|Jantar|Almoço|Refeiç|Servimos|Lav\.|Check|Chek|Pagamento|Reservas|Atendimento|Fechado|Horário|Contato|Jantar)',s2,re.I) or re.search(r'R\$',s2):
                extras.append(s2); zone=False; continue
            if STREET.match(s2) or inaddr:
                addr.append(s2); inaddr=True; continue
            if re.match(r'^[\w._]+$',s2) and not s2[0].isupper() and len(s2)>5: social.append(s2); continue
            other.append(s2)
        if not addr and other:
            addr=other[:]
        # address continuation lines (e.g. '50 m do Posto Shell') appended to addr already via inaddr
        obsl=[s for _,s in lines(obsw) if not re.match(r'^(Observações|Cidade|Pousada)\b',s)]
        # city / km
        if hk in('A',):
            kt=cell_text(p,words,*H['km'],kseps,b['top']+2)
            ct=cell_text(p,words,*H['city'],cseps,b['top']+2)
        else:
            ct=cell_text(p,words,*H['city'],cseps,b['top']+2); kt=ct
        km,dist,ramal,kraw=kmparse(kt)
        def kmish(l):
            return bool(re.fullmatch(r'[\d.,\s]*[PG]?\s*',l.strip()) or re.search(r'\bfora\b|da trilha|sentido|do início|do inicio|do Santuário|\d\s*(km|Km|mt|m)\b|Cidade|^\d+,?\d*\s*[PG],?$',l))
        cityl=[s for _,s in ct if not kmish(s)]
        city=' '.join(cityl)
        seen=[];
        for part in re.split(r'(?<=/SP\))|(?<=/MG\))',city): pass
        toks=city.split(); 
        # dedupe immediate repeated phrase
        half=len(toks)//2
        if half and toks[:half]==toks[half:2*half] and len(toks)==2*half: toks=toks[:half]
        city=' '.join(toks).strip()
        inherited=[]
        if city: state.setdefault('city',{})[hk]=city
        else:
            city=state.get('city',{}).get(hk,'')
            inherited.append('cidade herdada')
        if km is None and dist is None and ramal is None and not city.startswith(('Águas da Prata','Aparecida')):
            pass
        if km is not None: state.setdefault('km',{})[hk]=(km,ramal)
        elif not city.startswith(('Águas da Prata','Aparecida')) and not re.search(r'fora da trilha|verificar',kraw) :
            pk=state.get('km',{}).get(hk)
            if pk: km,ramal=pk; inherited.append('km herdado do registro anterior')
        ptxt=' | '.join(price_lines)
        res.append(dict(pagina=pi+1,col=hk,nome=re.sub(r'\s+',' ',name).strip(),cidade_raw=city,km_raw=kraw.strip(),km_pdf=km,dist=dist,ramal=ramal,
            telefones=phones,contato=contact,credencial=cred or any('CREDENCIAL' in s for _,s in ul),emails=email,sites=web,
            preco_texto=ptxt,precos=money(ptxt),extras=extras,endereco=' '.join(addr),social=social,outros=other,obs=obsl,
            _y=b['top'],heranca=inherited,_band=[top,nxt],_obsx=list(H['obs'])))
    return res
STATE={}
def main():
    out=[]
    with pdfplumber.open(F) as pdf:
        for pi,p in enumerate(pdf.pages):
            if pi<1: continue
            img=p.to_image(resolution=72*S).original
            out+=parse_page(pi,p,img,STATE)
    return out
