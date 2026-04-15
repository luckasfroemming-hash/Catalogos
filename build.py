import urllib.request, re, json, time, os, sys

BASE    = 'https://ovosneaker.x.yupoo.com'
CDN     = 'https://photo.yupoo.com/ovosneaker/'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Referer'   : BASE + '/',
}
BAD = {'whatsapp','instagram','discord','wechat','telegram','groups','spreadsheet'}

def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=25) as r:
                return r.read().decode('utf-8', errors='ignore')
        except Exception as e:
            if i == tries-1: print('FAIL', url, e); return ''
            time.sleep(3*(i+1))
    return ''

def dl(h):
    p = 'images/' + h + '.jpg'
    if os.path.exists(p): return True
    try:
        req = urllib.request.Request(CDN+h+'/medium.jpg', headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as r:
            d = r.read()
        if len(d) > 2000:
            open(p, 'wb').write(d); return True
    except: pass
    return False

def clean(t):
    for w in BAD:
        i = t.lower().find(w)
        if i > 0: t = t[:i]
    t = re.sub(r'\+\d[\d\s-]+', '', t)
    t = re.sub(r'[\u300a-\u300f][^\u300a-\u300f]*[\u300a-\u300f]', '', t)
    return t.strip() or 'Produto'

def parse(html, cat):
    albums, seen = [], set()
    lr = re.compile(r'href="https://ovosneaker\.x\.yupoo\.com/albums/(\d+)[^"]*"\s+[^>]*title="([^"]+)"')
    ir = re.compile(r'/([a-f0-9]{8})/(?:medium|small)\.jpg')
    ms = list(lr.finditer(html))
    for idx, m in enumerate(ms):
        aid, title = m.group(1), m.group(2)
        if aid in seen or any(w in title.lower() for w in BAD): continue
        end = ms[idx+1].start() if idx+1 < len(ms) else len(html)
        img = ir.search(html[m.start():end])
        if not img: continue
        seen.add(aid)
        albums.append({'id':aid,'title':clean(title),'cover':img.group(1),'cat':cat,'photos':[img.group(1)]})
    return albums

def catname(html):
    m = re.search(r'<title>([^<|]+)', html)
    if not m: return ''
    n = re.sub(r'whatsapp.*', '', m.group(1), flags=re.I)
    n = re.sub(r'(ovosneaker|Supplier|Catalog|分类).*', '', n, flags=re.I)
    return n.strip(' |-.')[:60]

os.makedirs('images', exist_ok=True)
print('=== Fetching main page ===')
main = fetch(BASE + '/albums')
subs = list(dict.fromkeys(re.findall(r'/categories/(\d+)\?isSubCate=true', main)))
tops = list(dict.fromkeys(re.findall(r'/categories/(\d+)"', main)))
ids  = list(dict.fromkeys(subs + tops))
print(f'Categories: {len(ids)}')

albums, seen = [], set()
for i, cid in enumerate(ids):
    url = BASE + '/categories/' + cid + ('?isSubCate=true' if cid in subs else '')
    print(f'[{i+1}/{len(ids)}] cat {cid}', end=' ')
    html = fetch(url)
    if not html: print('skip'); continue
    name = catname(html) or 'Cat'+cid
    found = [a for a in parse(html, name) if a['id'] not in seen]
    for a in found: seen.add(a['id'])
    albums.extend(found)
    print(f'-> {len(found)} new, total={len(albums)}, cat="{name}"')
    time.sleep(0.5)

print(f'\n=== {len(albums)} albums total ===')
json.dump(albums, open('catalog.json','w', encoding='utf-8'), ensure_ascii=False)

print('\n=== Downloading images ===')
ok = 0
for i, a in enumerate(albums):
    if dl(a['cover']): ok += 1; print(f'[{i+1}/{len(albums)}] OK {a["cover"]}')
    else: print(f'[{i+1}/{len(albums)}] FAIL {a["cover"]}')
    time.sleep(0.2)
print(f'\nDone: {ok}/{len(albums)} images downloaded')

print('\n=== Generating index.html ===')
cats = list(dict.fromkeys(a['cat'] for a in albums))
pj   = json.dumps(albums, ensure_ascii=False)
cj   = json.dumps(cats,   ensure_ascii=False)

css = open('style.css').read() if os.path.exists('style.css') else ''

page = (
'<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">'
'<meta name="viewport" content="width=device-width,initial-scale=1.0">'
'<title>Catalogo</title>'
'<link rel="stylesheet" href="style.css">'
'</head><body>'
'<aside id="sb"><div class="logo"><h1>CATALOGO</h1><p>Premium</p></div>'
'<div class="srch"><input id="si" placeholder="Buscar..." autocomplete="off"></div>'
'<nav id="nav"></nav></aside>'
'<main><div class="topbar"><h2 id="ttl">CATALOGO</h2><span id="tsub"></span></div>'
'<div class="pc" id="pc"></div>'
'<footer><p>CATALOGO</p><p id="yr"></p></footer></main>'
'<div id="lb"><button id="lbx">x</button><div id="lbn"></div>'
'<div class="lbw"><button class="la" id="lbp"><</button>'
'<img id="lbi" src="" alt=""><button class="la" id="lbnx">></button></div>'
'<div id="lbs"></div><div id="lbt"></div></div>'
'<button id="mob">|||</button>'
'<script>var P=' + pj + ';var C=' + cj + ';</script>'
'<script src="app.js"></script>'
'</body></html>'
)
open('index.html','w',encoding='utf-8').write(page)
print('Done. index.html generated with', len(albums), 'products')
