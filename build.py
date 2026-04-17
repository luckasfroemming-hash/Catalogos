#!/usr/bin/env python3
"""
build.py v3 — Scraper Yupoo usando categorias NATIVAS do Yupoo.
"""
import os
import re
import json
import time
import urllib.request
import urllib.parse
import ssl
import subprocess
from pathlib import Path

BASE = "https://ovosneaker.x.yupoo.com"
CDN = "https://photo.yupoo.com/ovosneaker/"
OUT_DIR = Path("images")
DATA_FILE = Path("data.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": BASE + "/",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

CENSOR_PATTERNS = [
    re.compile(r"【\s*\d+\s*[yY]\s*】", re.IGNORECASE),
    re.compile(r"\[\s*\d+\s*[yY]\s*\]", re.IGNORECASE),
    re.compile(r"ovosneaker", re.IGNORECASE),
    re.compile(r"whatsapp[\s:+]*\+?\d[\d\s\-]+", re.IGNORECASE),
    re.compile(r"wechat[\s:+]*[\w\-]+", re.IGNORECASE),
    re.compile(r"\+?86[\s\-]?\d{3}[\s\-]?\d{4}[\s\-]?\d{4}", re.IGNORECASE),
    re.compile(r"supplier product catalog", re.IGNORECASE),
]

EXCLUDE_TITLES = [
    "whatsapp", "instagram", "discord", "telegram", "cssbuy",
    "spreadsheet", "ovo spreadsheet", "groups",
]

CATEGORY_BRAND_MAP = {
    "dunk": "Nike Dunk",
    "aj1": "Air Jordan 1",
    "aj3": "Air Jordan 3",
    "aj4": "Air Jordan 4",
    "aj5": "Air Jordan 5",
    "aj6": "Air Jordan 6",
    "aj11": "Air Jordan 11",
    "aj12": "Air Jordan 12",
    "aj13": "Air Jordan 13",
    "air max": "Nike Air Max",
    "air more uptempo": "Nike Air More Uptempo",
    "yeezy": "Adidas Yeezy",
    "adi-das": "Adidas",
    "adidas": "Adidas",
    "nk": "Nike",
    "1v": "Louis Vuitton",
    "d-i-o-r": "Dior",
    "dior": "Dior",
    "tim-berland": "Timberland",
    "timberland": "Timberland",
    "kobe": "Nike Kobe",
    "mai-son-mar-giela": "Maison Margiela",
    "margiela": "Maison Margiela",
    "camisas de futebol": "Camisas de Futebol",
    "mihara yasuhiro": "Mihara Yasuhiro",
    "nb": "New Balance",
    "new balance": "New Balance",
    "van-s": "Vans",
    "vans": "Vans",
    "pu-ma": "Puma",
    "puma": "Puma",
    "asics": "Asics",
    "onitsuka": "Onitsuka Tiger",
    "converse": "Converse",
    "amiri": "AMIRI",
    "a-miri": "AMIRI",
    "gucci": "Gucci",
    "prada": "Prada",
    "balenciaga": "Balenciaga",
    "reebok": "Reebok",
    "ugg": "UGG",
    "u-g-g": "UGG",
    "chrome": "Chrome Hearts",
    "galaxy": "Nike Galaxy",
    "sb": "Nike SB",
    "salomon": "Salomon",
    "on running": "On Running",
    "on cloud": "On Running",
    "mizuno": "Mizuno",
    "mcqueen": "Alexander McQueen",
    "mc-queen": "Alexander McQueen",
    "kids": "Infantil",
    "child": "Infantil",
    "cortez": "Nike Cortez",
    "shox": "Nike Shox",
    "vapormax": "Nike Vapormax",
    "samba": "Adidas Samba",
    "gazelle": "Adidas Gazelle",
    "forum": "Adidas Forum",
    "superstar": "Adidas Superstar",
    "foam runner": "Adidas Yeezy",
    "fear": "Fear of God",
    "fog": "Fear of God",
    "miu-miu": "Miu Miu",
    "miu miu": "Miu Miu",
    "ggdb": "Golden Goose",
    "bad bunny": "Bad Bunny x Adidas",
    "crocs": "Crocs",
    "cro-cs": "Crocs",
    "nike": "Nike",
}

def clean_title(raw):
    t = raw or ""
    for pat in CENSOR_PATTERNS:
        t = pat.sub("", t)
    t = re.sub(r"^[\s\|\-–—]+", "", t)
    t = re.sub(r"[\s\|\-–—]+$", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t or "Produto"

def clean_category_name(raw):
    t = raw or ""
    t = re.sub(r"[【〖《\[][^】〗》\]]*[】〗》\]]", "", t)
    t = re.sub(r"^\s*\w+\s+batch\s+", "", t, flags=re.IGNORECASE)
    t = t.replace("-", " ").strip()
    t = re.sub(r"\s+", " ", t)
    return t

def should_exclude_title(title):
    low = title.lower()
    return any(bad in low for bad in EXCLUDE_TITLES)

def slugify(s):
    s = (s or "").lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s or "item"

def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
                return r.read().decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"  fetch fail [{i+1}/{tries}] {url}: {e}")
            if i < tries - 1:
                time.sleep(3 * (i + 1))
    return ""

def download_image(hash_id, dest):
    if dest.exists() and dest.stat().st_size > 1500:
        return True
    for size in ["medium", "small"]:
        url = f"{CDN}{hash_id}/{size}.jpg"
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
                data = r.read()
            if len(data) > 2000:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                return True
        except Exception:
            continue
    return False

def extract_categories_from_home():
    print("Buscando estrutura de categorias...")
    html = fetch(BASE + "/")
    if not html:
        print("FALHA ao acessar home!")
        return []
    cats = []
    seen_ids = set()
    for m in re.finditer(
        r'href="(?:https?://[^"]*?)?/categories/(\d+)(?:\?[^"]*)?"[^>]*>([^<]+)</a>',
        html,
    ):
        cat_id = m.group(1)
        name = m.group(2).strip()
        if cat_id in seen_ids or not name:
            continue
        seen_ids.add(cat_id)
        cats.append({"id": cat_id, "raw_name": name})
    print(f"  {len(cats)} categorias encontradas")
    return cats

def categorize_by_brand(cat_name):
    low = (cat_name or "").lower()
    for key in sorted(CATEGORY_BRAND_MAP.keys(), key=lambda k: -len(k)):
        if key in low:
            return CATEGORY_BRAND_MAP[key]
    cleaned = clean_category_name(cat_name)
    return cleaned or "Outros"

def extract_albums_from_category(cat_id):
    albums = []
    seen_ids = set()
    for page in range(1, 30):
        url = f"{BASE}/categories/{cat_id}?page={page}&uid=1"
        html = fetch(url)
        if not html:
            break

        found_in_page = 0
        album_blocks = re.finditer(
            r'href="(?:https?://[^"]*?)?/albums/(\d+)[^"]*"(?:[^>]*?title="([^"]+)")?',
            html,
        )
        album_titles = {}
        for m in album_blocks:
            aid = m.group(1)
            title = m.group(2) or ""
            if aid in album_titles and not title:
                continue
            album_titles[aid] = title

        for aid, title in album_titles.items():
            if aid in seen_ids:
                continue
            pattern = (
                r'albums/' + aid + r'[^"]*"[^>]*>.*?'
                r'photo\.yupoo\.com/ovosneaker/([a-f0-9]+)/'
            )
            hash_m = re.search(pattern, html, re.DOTALL)
            img_hash = hash_m.group(1) if hash_m else None

            if not title:
                title_m = re.search(
                    r'albums/' + aid + r'[^"]*".*?<h[1-6][^>]*>([^<]+)</h',
                    html, re.DOTALL
                )
                if title_m:
                    title = title_m.group(1).strip()

            title = clean_title(title)
            if should_exclude_title(title):
                continue

            seen_ids.add(aid)
            albums.append({
                "id": aid,
                "title": title,
                "hash": img_hash,
            })
            found_in_page += 1

        if found_in_page == 0:
            break
        time.sleep(0.3)

    return albums

def extract_images_from_album(album_id):
    url = f"{BASE}/albums/{album_id}?uid=1"
    html = fetch(url)
    if not html:
        return []
    hashes = re.findall(
        r'photo\.yupoo\.com/ovosneaker/([a-f0-9]+)/',
        html,
    )
    seen = set()
    out = []
    for h in hashes:
        if h in seen:
            continue
        seen.add(h)
        out.append(h)
    return out

def git_commit_push(message):
    try:
        subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
        diff = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
        if diff.returncode == 0:
            return False
        subprocess.run(["git", "commit", "-m", message], check=True, capture_output=True)
        subprocess.run(["git", "push"], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  git erro: {e}")
        return False

def main():
    data = {"categorias": [], "total_albuns": 0, "total_imagens": 0}
    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text())
        except Exception:
            pass

    done_albums = set()
    cat_index = {}
    for c in data.get("categorias", []):
        cat_index[c["nome"]] = c
        for a in c.get("albuns", []):
            done_albums.add(a["id"])
    print(f"Retomando: {len(done_albums)} albuns ja processados")

    categories = extract_categories_from_home()
    if not categories:
        print("Sem categorias, abortando")
        return

    brand_categories = {}
    for cat in categories:
        brand = categorize_by_brand(cat["raw_name"])
        brand_categories.setdefault(brand, []).append(cat)

    print(f"\nTotal de marcas apos agrupamento: {len(brand_categories)}")
    for b, cs in brand_categories.items():
        print(f"  {b}: {len(cs)} categoria(s)")

    for brand, cats in brand_categories.items():
        brand_slug = slugify(brand)
        print(f"\n=== Processando marca: {brand} ({len(cats)} cats) ===")

        if brand not in cat_index:
            cat_index[brand] = {"nome": brand, "slug": brand_slug, "albuns": []}

        novos_nesta_marca = 0
        for cat in cats:
            print(f"  Categoria: {cat['raw_name']} (id={cat['id']})")
            albums = extract_albums_from_category(cat["id"])
            print(f"    {len(albums)} albuns encontrados")

            for alb in albums:
                if alb["id"] in done_albums:
                    continue

                img_hashes = extract_images_from_album(alb["id"])
                if not img_hashes:
                    if alb["hash"]:
                        img_hashes = [alb["hash"]]
                    else:
                        continue

                saved = []
                for i, h in enumerate(img_hashes):
                    dest = OUT_DIR / brand_slug / alb["id"] / f"{i:03d}.jpg"
                    if download_image(h, dest):
                        saved.append(str(dest).replace("\\", "/"))

                if not saved:
                    continue

                cat_index[brand]["albuns"].append({
                    "id": alb["id"],
                    "titulo": alb["title"],
                    "capa": saved[0],
                    "imagens": saved,
                })
                done_albums.add(alb["id"])
                novos_nesta_marca += 1

                if novos_nesta_marca % 5 == 0:
                    print(f"    +{novos_nesta_marca} novos em {brand}, ultimo: {alb['title'][:50]}")
                time.sleep(0.2)

        if novos_nesta_marca > 0:
            data["categorias"] = sorted(
                list(cat_index.values()),
                key=lambda c: (-len(c["albuns"]), c["nome"]),
            )
            data["total_albuns"] = sum(len(c["albuns"]) for c in data["categorias"])
            data["total_imagens"] = sum(
                len(a["imagens"])
                for c in data["categorias"]
                for a in c["albuns"]
            )
            DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
            print(f"  Salvando {brand}: +{novos_nesta_marca} albuns. TOTAL: {data['total_albuns']} albuns, {data['total_imagens']} imgs")
            if git_commit_push(f"Progresso [{brand}]: +{novos_nesta_marca} albuns"):
                print(f"  -> commit + push OK")

    data["categorias"] = sorted(
        list(cat_index.values()),
        key=lambda c: (-len(c["albuns"]), c["nome"]),
    )
    data["total_albuns"] = sum(len(c["albuns"]) for c in data["categorias"])
    data["total_imagens"] = sum(
        len(a["imagens"]) for c in data["categorias"] for a in c["albuns"]
    )
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    git_commit_push(f"Build final: {data['total_albuns']} albuns, {data['total_imagens']} imgs")
    print(f"\nFINAL: {len(data['categorias'])} marcas, {data['total_albuns']} albuns, {data['total_imagens']} imagens")

if __name__ == "__main__":
    main()

