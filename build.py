import urllib.request, urllib.error, re, json, time, os, sys, traceback

BASE    = 'https://ovosneaker.x.yupoo.com'
CDN     = 'https://photo.yupoo.com/ovosneaker/'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer'   : BASE + '/',
    'Accept'    : 'text/html,application/xhtml+xml,*/*;q=0.8',
}
BAD = ['whatsapp','instagram','discord','wechat','telegram','groups','spreadsheet']

# ── network ──────────────────────────────────────────────────────────────────

def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            ctx = __import__('ssl').create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = __import__('ssl').CERT_NONE
            with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
                return r.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f'  fetch attempt {i+1} failed: {e}')
            if i < tries-1:
                time.sleep(4*(i+1))
    return ''

def dl(h):
    path = 'images/' + h + '.jpg'
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return True
    for size in ['medium', 'small']:
        try:
            url = CDN + h + '/' + size + '.jpg'
            req = urllib.request.Request(url, headers=HEADERS)
            ctx = __import__('ssl').create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = __import__('ssl').CERT_NONE
            with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
                data = r.read()
            if len(data) > 2000:
                with open(path, 'wb') as f:
                    f.write(data)
                return True
        except Exception as e:
            print(f'  dl {size} failed: {e}')
    return False

# ── parsing ───────────────────────────────────────────────────────────────────

def clean(t):
    try:
        for w in BAD:
            idx = t.lower().find(w)
            if 0 < idx < len(t):
                t = t[:idx]
        t = re.sub(r'\+\d[\d\s\-]+', '', t)
        t = re.sub(r'[【〖][^】〗]*[】〗]', '', t)
        t = re.sub(r'\s+', ' ', t).strip()
        return t or 'Produto'
    except Exception:
        return 'Produto'

def catname(html):
    try:
        m = re.search(r'<title>([^<]+)', html)
        if not m:
            return ''
        n = m.group(1)
        for pat in [r'(?i)whatsapp.*', r'(?i)ovosneaker.*', r'(?i)supplier.*',
                    r'(?i)catalog.*', r'分类.*', r'\|.*']:
            n = re.sub(pat, '', n)
        return n.strip(' |-.')[:60]
    except Exception:
        return ''

def parse_albums(html, cat_name):
    albums = []
    seen   = set()
    try:
        # Pattern: find album links with title attribute
        # Two possible orderings: href first, or title first
        patterns = [
            re.compile(r'href="https://ovosneaker\.x\.yupoo\.com/albums/(\d+)[^"]*"[^>]+title="([^"]+)"'),
            re.compile(r'title="([^"]+)"[^>]+href="https://ovosneaker\.x\.yupoo\.com/albums/(\d+)[^"]*"'),
        ]
        img_re = re.compile(r'/([a-f0-9]{8})/(?:medium|small)\.jpg')

        for pat_idx, pat in enumerate(patterns):
            ms = list(pat.finditer(html))
            for i, m in enumerate(ms):
                if pat_idx == 0:
                    aid, title = m.group(1), m.group(2)
                else:
                    title, aid = m.group(1), m.group(2)

                if not aid.isdigit():
                    continue
                if aid in seen:
                    continue
                if any(w in title.lower() for w in BAD):
                    continue

                seen.add(aid)

                # Find cover image after this link
                end = ms[i+1].start() if i+1 < len(ms) else min(m.start()+2000, len(html))
                chunk = html[m.start():end]
                img_m = img_re.search(chunk)
                cover = img_m.group(1) if img_m else None
                if not cover:
                    continue

                albums.append({
                    'id'    : aid,
                    'title' : clean(title),
                    'cover' : cover,
                    'cat'   : cat_name,
                    'photos': [cover],
                })

    except Exception as e:
        print(f'  parse error: {e}')
        traceback.print_exc()

    return albums

# ── main ──────────────────────────────────────────────────────────────────────

os.makedirs('images', exist_ok=True)

print('='*60)
print('STEP 1: Fetching main page')
print('='*60)
main_html = fetch(BASE + '/albums')
if not main_html:
    print('ERROR: could not fetch main page')
    sys.exit(1)
print(f'Main page fetched: {len(main_html)} chars')

sub_ids = list(dict.fromkeys(re.findall(r'/categories/(\d+)\?isSubCate=true', main_html)))
top_ids = list(dict.fromkeys(re.findall(r'/categories/(\d+)"', main_html)))
all_ids = list(dict.fromkeys(sub_ids + top_ids))
print(f'Found {len(sub_ids)} subcategories + {len(top_ids)} top-level = {len(all_ids)} total')

print('\n' + '='*60)
print('STEP 2: Scraping each category')
print('='*60)
albums   = []
seen_ids = set()

for i, cid in enumerate(all_ids):
    is_sub = cid in sub_ids
    url    = BASE + '/categories/' + cid + ('?isSubCate=true' if is_sub else '')
    print(f'[{i+1}/{len(all_ids)}] cat {cid}', end=' ... ')
    sys.stdout.flush()

    try:
        html = fetch(url)
        if not html:
            print('SKIP (empty response)')
            continue

        name  = catname(html) or ('Sub' if is_sub else 'Cat') + cid
        found = [a for a in parse_albums(html, name) if a['id'] not in seen_ids]
        for a in found:
            seen_ids.add(a['id'])
        albums.extend(found)
        print(f'{len(found)} new albums | total={len(albums)} | "{name}"')
    except Exception as e:
        print(f'ERROR: {e}')
        traceback.print_exc()

    time.sleep(0.5)

print(f'\nTotal albums collected: {len(albums)}')

if not albums:
    print('WARNING: no albums found! Check if site structure changed.')

print('\n' + '='*60)
print('STEP 3: Saving catalog.json')
print('='*60)
try:
    with open('catalog.json', 'w', encoding='utf-8') as f:
        json.dump(albums, f, ensure_ascii=False, indent=None)
    print(f'Saved {len(albums)} albums to catalog.json')
except Exception as e:
    print(f'ERROR saving catalog.json: {e}')
    traceback.print_exc()
    sys.exit(1)

print('\n' + '='*60)
print('STEP 4: Downloading cover images')
print('='*60)
ok_count = fail_count = 0
for i, a in enumerate(albums):
    try:
        result = dl(a['cover'])
        if result:
            ok_count += 1
            print(f'[{i+1}/{len(albums)}] OK  {a["cover"]}')
        else:
            fail_count += 1
            print(f'[{i+1}/{len(albums)}] FAIL {a["cover"]} | {a["title"][:40]}')
    except Exception as e:
        fail_count += 1
        print(f'[{i+1}/{len(albums)}] ERR  {a["cover"]}: {e}')
    time.sleep(0.2)

print(f'\nImages: {ok_count} OK, {fail_count} failed')

print('\n' + '='*60)
print('STEP 5: Generating index.html')
print('='*60)
try:
    cats  = list(dict.fromkeys(a['cat'] for a in albums))
    pj    = json.dumps(albums, ensure_ascii=False)
    cj    = json.dumps(cats,   ensure_ascii=False)

    parts = [
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
        '<div id="lbs"></div>',
        '<div id="lbt"></div>',
        '</div>',
        '<button id="mob">&#9776;</button>',
        '<script>',
        'var P=', pj, ';',
        'var C=', cj, ';',
        '</script>',
        '<script src="app.js"></script>',
        '</body></html>',
    ]

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(''.join(parts))

    size = os.path.getsize('index.html')
    print(f'index.html generated: {size} bytes, {len(albums)} products, {len(cats)} categories')
except Exception as e:
    print(f'ERROR generating index.html: {e}')
    traceback.print_exc()
    sys.exit(1)

print('\n' + '='*60)
print('ALL DONE')
print('='*60)
