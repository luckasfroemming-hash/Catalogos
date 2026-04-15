import urllib.request, re, json, time, os, sys, ssl, traceback

BASE    = 'https://ovosneaker.x.yupoo.com'
CDN     = 'https://photo.yupoo.com/ovosneaker/'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120',
    'Referer'   : BASE + '/',
    'Accept'    : 'text/html,application/xhtml+xml,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}
BAD = ['whatsapp','instagram','discord','wechat','telegram','spreadsheet']
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode    = ssl.CERT_NONE

def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
                return r.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f'  [{i+1}/{tries}] FAIL {url}: {e}')
            if i < tries-1: time.sleep(5*(i+1))
    return ''

def dl(h):
    p = 'images/' + h + '.jpg'
    if os.path.exists(p) and os.path.getsize(p) > 1000:
        return True
    for size in ['medium','small']:
        try:
            req = urllib.request.Request(CDN+h+'/'+size+'.jpg', headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
                d = r.read()
            if len(d) > 2000:
                open(p,'wb').write(d)
                return True
        except: pass
    return False

def clean(t):
    if not t: return 'Produto'
    for w in BAD:
        i = t.lower().find(w)
        if 0 < i < len(t): t = t[:i]
    t = re.sub(r'\+\d[\d\s-]+','',t)
    t = re.sub(r'[【〖《][^】〗》]*[】〗》]','',t)
    return re.sub(r'\s+',' ',t).strip() or 'Produto'

def parse(html, cat):
    """
    Robust album parser — tries multiple strategies.
    Yupoo category pages have album items in a grid.
    The album ID is in the href, cover image is nearby.
    Title may be in: title attribute, alt attribute, or adjacent text.
    """
    albums = []
    seen   = set()

    # Strategy 1: href with full domain URL
    # Strategy 2: href with relative URL /albums/ID
    LINK_PATTERNS = [
        re.compile(r'href="(?:https?://ovosneaker\.x\.yupoo\.com)?/albums/(\d+)[^"]*"'),
    ]
    IMG_RE   = re.compile(r'photo\.yupoo\.com/ovosneaker/([a-f0-9]{8})/(?:medium|small)\.jpg')
    TITLE_RE = re.compile(r'(?:title|alt)="([^"]{2,120})"')
    TEXT_RE  = re.compile(r'>([^<\n]{3,80})<')

    for link_pat in LINK_PATTERNS:
        ms = list(link_pat.finditer(html))
        print(f'  Link pattern found {len(ms)} matches')

        for idx, m in enumerate(ms):
            aid = m.group(1)
            if not aid.isdigit() or aid in seen:
                continue

            # Look at a window around the link for image + title
            start = max(0, m.start() - 100)
            end   = min(len(html), m.end() + 1500)
            window = html[start:end]

            # Find cover image hash
            img_m = IMG_RE.search(window)
            if not img_m:
                continue

            # Find title: check the <a> tag itself first
            a_tag = m.group(0)
            title_m = TITLE_RE.search(a_tag)
            title = title_m.group(1) if title_m else ''

            # If not found in <a>, check surrounding 600 chars
            if not title:
                nearby = html[m.end():min(len(html), m.end()+600)]
                title_m = TITLE_RE.search(nearby)
                if title_m:
                    title = title_m.group(1)

            # Last resort: adjacent visible text
            if not title:
                text_m = TEXT_RE.search(html[m.end():min(len(html), m.end()+300)])
                if text_m:
                    title = text_m.group(1).strip()

            if not title:
                title = 'Produto ' + aid

            if any(w in title.lower() for w in BAD):
                continue

            seen.add(aid)
            albums.append({
                'id'    : aid,
                'title' : clean(title),
                'cover' : img_m.group(1),
                'cat'   : cat,
                'photos': [img_m.group(1)],
            })

    return albums

def catname(html):
    try:
        m = re.search(r'<title>([^<]+)', html)
        if not m: return ''
        n = m.group(1)
        for pat in [r'(?i)whatsapp.*',r'(?i)ovosneaker.*',r'(?i)supplier.*',
                    r'(?i)catalog.*',r'分类.*',r'\|.*']:
            n = re.sub(pat,'',n)
        return n.strip(' |-.') [:60]
    except: return ''

# ─── MAIN ────────────────────────────────────────────────────────────────────

os.makedirs('images', exist_ok=True)

print('='*60)
print('STEP 1: Fetch main albums page')
main = fetch(BASE + '/albums')
print(f'Got {len(main)} chars')

# Show a snippet of HTML to help debug structure
snippet = main[5000:5500] if len(main) > 5000 else main[:500]
print('HTML snippet (5000-5500):')
print(snippet)
print()

sub_ids = list(dict.fromkeys(re.findall(r'/categories/(\d+)\?isSubCate=true', main)))
top_ids = list(dict.fromkeys(re.findall(r'/categories/(\d+)"', main)))
all_ids = list(dict.fromkeys(sub_ids + top_ids))
print(f'Categories: {len(sub_ids)} sub + {len(top_ids)} top = {len(all_ids)} total')

# Also try to parse albums directly from the main page
print('\nParsing albums from main page directly...')
main_albums = parse(main, 'Destaque')
print(f'Found {len(main_albums)} albums on main page')

print('\n' + '='*60)
print('STEP 2: Scrape each category')
albums   = []
seen_ids = set()

# Start with albums found on main page
for a in main_albums:
    if a['id'] not in seen_ids:
        seen_ids.add(a['id'])
        albums.append(a)

for i, cid in enumerate(all_ids):
    is_sub = cid in sub_ids
    url    = BASE + '/categories/' + cid + ('?isSubCate=true' if is_sub else '')
    print(f'\n[{i+1}/{len(all_ids)}] cat {cid} {"(sub)" if is_sub else ""}')

    try:
        html = fetch(url)
        if not html:
            print('  SKIP: empty response')
            continue

        print(f'  Got {len(html)} chars')

        # Show link count for debugging
        abs_links = len(re.findall(r'href="https://ovosneaker\.x\.yupoo\.com/albums/', html))
        rel_links = len(re.findall(r'href="/albums/', html))
        imgs      = len(re.findall(r'photo\.yupoo\.com/ovosneaker/', html))
        print(f'  abs album links: {abs_links}, rel album links: {rel_links}, images: {imgs}')

        name  = catname(html) or ('Sub' if is_sub else 'Cat') + cid
        found = [a for a in parse(html, name) if a['id'] not in seen_ids]
        for a in found: seen_ids.add(a['id'])
        albums.extend(found)
        print(f'  -> {len(found)} new | total={len(albums)} | "{name}"')

    except Exception as e:
        print(f'  ERROR: {e}')
        traceback.print_exc()

    time.sleep(0.5)

print(f'\n{"="*60}')
print(f'TOTAL: {len(albums)} albums found')

print('\nSTEP 3: Save catalog.json')
try:
    with open('catalog.json','w',encoding='utf-8') as f:
        json.dump(albums, f, ensure_ascii=False)
    print(f'Saved {len(albums)} albums')
except Exception as e:
    print(f'ERROR: {e}'); traceback.print_exc()

print('\nSTEP 4: Download images')
ok = fail = 0
for i, a in enumerate(albums):
    try:
        if dl(a['cover']): ok += 1; print(f'[{i+1}/{len(albums)}] OK  {a["cover"]}')
        else:              fail+=1; print(f'[{i+1}/{len(albums)}] FAIL {a["cover"]}')
    except Exception as e:
        fail += 1; print(f'[{i+1}/{len(albums)}] ERR {e}')
    time.sleep(0.2)
print(f'Images: {ok} OK, {fail} failed')

print('\nSTEP 5: Generate index.html')
try:
    cats = list(dict.fromkeys(a['cat'] for a in albums))
    pj   = json.dumps(albums, ensure_ascii=False)
    cj   = json.dumps(cats,   ensure_ascii=False)
    page = ''.join([
        '<!DOCTYPE html><html lang="pt-BR"><head>',
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1.0">',
        '<title>Catalogo</title>',
        '<link rel="stylesheet" href="style.css">',
        '</head><body>',
        '<aside id="sb">',
        '<div class="logo"><h1>CATALOGO</h1><p>Premium</p></div>',
        '<div class="srch"><input id="si" placeholder="Buscar..." autocomplete="off"></div>',
        '<nav id="nav"></nav></aside>',
        '<main>',
        '<div class="topbar"><h2 id="ttl">CATALOGO</h2><span id="tsub"></span></div>',
        '<div class="pc" id="pc"></div>',
        '<footer><p>CATALOGO DE PRODUTOS</p><p id="yr"></p></footer>',
        '</main>',
        '<div id="lb">',
        '<button id="lbx">&#x2715;</button>',
        '<div id="lbn"></div>',
        '<div class="lbw">',
        '<button class="la" id="lbp">&#8249;</button>',
        '<img id="lbi" src="" alt="">',
        '<button class="la" id="lbnx">&#8250;</button>',
        '</div>',
        '<div id="lbs"></div><div id="lbt"></div>',
        '</div>',
        '<button id="mob">&#9776;</button>',
        '<script>var P=', pj, ';var C=', cj, ';</script>',
        '<script src="app.js"></script>',
        '</body></html>',
    ])
    with open('index.html','w',encoding='utf-8') as f:
        f.write(page)
    print(f'index.html: {os.path.getsize("index.html")} bytes, {len(albums)} products, {len(cats)} cats')
except Exception as e:
    print(f'ERROR: {e}'); traceback.print_exc()

print('\n' + '='*60)
print('DONE')
