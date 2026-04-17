#!/usr/bin/env python3
"""
build.py — Scraper Yupoo com categorização por marca.

- Lista categorias do Yupoo
- Para cada categoria, lista álbuns
- Baixa imagens para images/<categoria-slug>/<album-id>/
- Gera data.json com {categorias: [{nome, slug, albuns: [{id, titulo, capa, imagens}]}]}
- Remove QUALQUER menção a "ovosneaker" nos títulos
- Classifica álbuns por MARCA (Nike, Adidas, Jordan, etc.) detectando no título
"""

import os
import re
import json
import time
import hashlib
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# ─── CONFIG ──────────────────────────────────────────────────────────────────
BASE_URL = "https://ovosneaker.x.yupoo.com"
OUT_DIR = Path("images")
DATA_FILE = Path("data.json")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": BASE_URL + "/",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "300"))
SLEEP = 0.3

# Termos a remover/censurar dos títulos
CENSOR_PATTERNS = [
    re.compile(r"【\s*\d+\s*[yY]\s*】", re.IGNORECASE),   # 【160y】 【 200Y 】 etc
    re.compile(r"\[\s*\d+\s*[yY]\s*\]", re.IGNORECASE),   # [160y] variante ASCII
    re.compile(r"ovosneaker", re.IGNORECASE),
    re.compile(r"whatsapp[\s:+]*\+?\d[\d\s\-]+", re.IGNORECASE),
    re.compile(r"wechat[\s:+]*[\w\-]+", re.IGNORECASE),
    re.compile(r"\+?86[\s\-]?\d{3}[\s\-]?\d{4}[\s\-]?\d{4}", re.IGNORECASE),
    re.compile(r"supplier product catalog", re.IGNORECASE),
    re.compile(r"\|\s*照片\s*\|", re.IGNORECASE),
]

# Marcas reconhecidas — ordem importa (mais específico primeiro)
BRANDS = [
    ("Air Jordan", ["air jordan", "aj1", "aj2", "aj3", "aj4", "aj5", "aj6",
                    "aj11", "aj12", "aj13", "jordan"]),
    ("Nike",      ["nike", "dunk", "sb dunk", "air force", "af1",
                   "air max", "vapormax", "cortez", "blazer"]),
    ("Adidas",    ["adidas", "yeezy", "samba", "gazelle", "spezial",
                   "campus", "forum", "stan smith", "superstar"]),
    ("New Balance", ["new balance", "nb 550", "nb550", "nb 9060",
                     "nb9060", "nb 2002", "nb 327"]),
    ("Asics",     ["asics", "gel-", "gel "]),
    ("Puma",      ["puma", "speedcat", "palermo", "suede"]),
    ("Converse",  ["converse", "chuck taylor", "chuck 70"]),
    ("Vans",      ["vans", "old skool", "sk8"]),
    ("Salomon",   ["salomon", "xt-6", "xt6", "xa pro"]),
    ("On Running", ["on running", "on cloud", "cloudmonster"]),
    ("Balenciaga", ["balenciaga", "triple s", "speed trainer"]),
    ("Louis Vuitton", ["louis vuitton", "lv trainer", "lv "]),
    ("Dior",      ["dior", "b22", "b23", "b30"]),
    ("Gucci",     ["gucci", "rhyton", "screener"]),
    ("Prada",     ["prada"]),
    ("Fear of God", ["fear of god", "fog"]),
    ("Reebok",    ["reebok", "club c", "classic leather"]),
    ("Timberland", ["timberland"]),
    ("Ugg",       ["ugg"]),
]

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def clean_title(raw: str) -> str:
    """Remove menções ao fornecedor e ruído."""
    t = raw or ""
    for pat in CENSOR_PATTERNS:
        t = pat.sub("", t)
    # Remove pipes/traços residuais no início/fim
    t = re.sub(r"^[\s\|\-–—]+", "", t)
    t = re.sub(r"[\s\|\-–—]+$", "", t)
    # Colapsa espaços
    t = re.sub(r"\s+", " ", t).strip()
    return t or "Produto"

def detect_brand(title: str) -> str:
    """Detecta marca pelo título do álbum."""
    t = title.lower()
    for brand, keywords in BRANDS:
        for kw in keywords:
            if kw in t:
                return brand
    return "Outros"

def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s or "item"

def fetch(url: str, retries: int = 3) -> requests.Response | None:
    """GET com retry."""
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                return None
            print(f"  ⚠ HTTP {r.status_code} em {url}")
        except requests.RequestException as e:
            print(f"  ⚠ erro {e} em {url}")
        time.sleep(1 + attempt)
    return None

def download_image(url: str, dest: Path) -> bool:
    """Baixa imagem se ainda não existe."""
    if dest.exists() and dest.stat().st_size > 1000:
        return True
    r = fetch(url)
    if not r:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    return True

# ─── SCRAPER ─────────────────────────────────────────────────────────────────

def list_categories() -> list[dict]:
    """Scrapeia página principal buscando links de categorias."""
    r = fetch(BASE_URL + "/categories")
    if not r:
        r = fetch(BASE_URL + "/")
    if not r:
        print("❌ Não consegui acessar a página inicial do Yupoo")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    cats = []
    seen = set()

    # Yupoo lista categorias como <a href="/categories/XXXXX">
    for a in soup.select("a[href*='/categories/']"):
        href = a.get("href", "")
        name = a.get_text(strip=True)
        if not href or not name:
            continue
        # Normaliza URL
        url = urljoin(BASE_URL, href)
        m = re.search(r"/categories/(\d+)", url)
        if not m:
            continue
        cat_id = m.group(1)
        if cat_id in seen:
            continue
        seen.add(cat_id)
        cats.append({
            "id": cat_id,
            "name": clean_title(name),
            "url": url,
        })
    print(f"📂 Encontradas {len(cats)} categorias no Yupoo")
    return cats

def list_albums_in_category(cat: dict) -> list[dict]:
    """Scrapeia álbuns de uma categoria (com paginação)."""
    albums = []
    page = 1
    while True:
        url = f"{cat['url']}?page={page}"
        r = fetch(url)
        if not r:
            break
        soup = BeautifulSoup(r.text, "html.parser")
        # Álbuns aparecem como <a class="album__main" href="/albums/XXXXX">
        cards = soup.select("a.album__main, a[href*='/albums/']")
        found_in_page = 0
        for a in cards:
            href = a.get("href", "")
            m = re.search(r"/albums/(\d+)", href)
            if not m:
                continue
            album_id = m.group(1)
            if any(x["id"] == album_id for x in albums):
                continue
            title = a.get("title") or a.get_text(strip=True) or ""
            # Tenta capturar imagem de capa
            img = a.select_one("img")
            cover = ""
            if img:
                cover = img.get("data-origin-src") or img.get("data-src") or img.get("src", "")
                if cover.startswith("//"):
                    cover = "https:" + cover
            albums.append({
                "id": album_id,
                "title": clean_title(title),
                "raw_title": title,
                "url": urljoin(BASE_URL, href.split("?")[0]),
                "cover_url": cover,
            })
            found_in_page += 1
        if found_in_page == 0:
            break
        page += 1
        time.sleep(SLEEP)
        if page > 50:  # safety
            break
    return albums

def list_images_in_album(album: dict) -> list[str]:
    """Scrapeia URLs de imagens de um álbum."""
    r = fetch(album["url"])
    if not r:
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    urls = []
    seen = set()
    for img in soup.select("img"):
        src = (img.get("data-origin-src")
               or img.get("data-src")
               or img.get("src", ""))
        if not src:
            continue
        if src.startswith("//"):
            src = "https:" + src
        if "photo.yupoo.com" not in src:
            continue
        # Pega a versão grande
        src = re.sub(r"/(small|medium|square)\.", "/", src)
        if src in seen:
            continue
        seen.add(src)
        urls.append(src)
    return urls

# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    # Carrega progresso anterior (pra retomar)
    data = {"categorias": [], "total_albuns": 0, "total_imagens": 0}
    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text())
            print(f"📄 Retomando — {data.get('total_albuns',0)} álbuns já salvos")
        except Exception:
            data = {"categorias": [], "total_albuns": 0, "total_imagens": 0}

    # === ESTRATÉGIA REAL ===
    # Não vamos usar categorias do Yupoo (vem em chinês / bagunçado).
    # Vamos listar TODOS os álbuns e classificar por MARCA via título.
    print("🔍 Listando TODOS os álbuns da home...")

    all_albums = []
    page = 1
    while True:
        url = f"{BASE_URL}/albums?page={page}"
        r = fetch(url)
        if not r:
            break
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select("a.album__main, a[href*='/albums/']")
        found = 0
        for a in cards:
            href = a.get("href", "")
            m = re.search(r"/albums/(\d+)", href)
            if not m:
                continue
            aid = m.group(1)
            if any(x["id"] == aid for x in all_albums):
                continue
            title = a.get("title") or a.get_text(strip=True) or ""
            img = a.select_one("img")
            cover = ""
            if img:
                cover = (img.get("data-origin-src")
                         or img.get("data-src")
                         or img.get("src", ""))
                if cover.startswith("//"):
                    cover = "https:" + cover
            all_albums.append({
                "id": aid,
                "title": clean_title(title),
                "url": urljoin(BASE_URL, href.split("?")[0]),
                "cover_url": cover,
            })
            found += 1
        print(f"  página {page}: +{found} álbuns (total: {len(all_albums)})")
        if found == 0:
            break
        page += 1
        time.sleep(SLEEP)
        if page > 100:
            break

    print(f"✅ Total de álbuns encontrados: {len(all_albums)}")

    # Classifica por marca
    brand_buckets: dict[str, list[dict]] = {}
    for alb in all_albums:
        brand = detect_brand(alb["title"])
        brand_buckets.setdefault(brand, []).append(alb)

    print(f"🏷 Marcas detectadas: {', '.join(f'{b}({len(v)})' for b,v in brand_buckets.items())}")

    # Processa álbum por álbum — baixa imagens, monta data.json
    # Faz em lotes pra commitar incrementalmente
    processed_count = 0
    already_processed_ids = set()
    for cat in data.get("categorias", []):
        for alb in cat.get("albuns", []):
            already_processed_ids.add(alb["id"])

    categorias_novas = {}
    # Começa com as categorias já salvas
    for cat in data.get("categorias", []):
        categorias_novas[cat["nome"]] = cat

    for brand, albums in brand_buckets.items():
        for alb in albums:
            if alb["id"] in already_processed_ids:
                continue
            print(f"  📦 {brand} / {alb['title'][:60]}")
            imgs = list_images_in_album(alb)
            if not imgs:
                time.sleep(SLEEP)
                continue

            brand_slug = slugify(brand)
            album_dir = OUT_DIR / brand_slug / alb["id"]
            saved_files = []
            for i, u in enumerate(imgs):
                ext = os.path.splitext(urlparse(u).path)[1] or ".jpg"
                fname = f"{i:03d}{ext}"
                dest = album_dir / fname
                if download_image(u, dest):
                    saved_files.append(f"images/{brand_slug}/{alb['id']}/{fname}")
                time.sleep(0.05)

            # Capa
            cover_local = saved_files[0] if saved_files else ""

            album_entry = {
                "id": alb["id"],
                "titulo": alb["title"],
                "capa": cover_local,
                "imagens": saved_files,
            }
            if brand not in categorias_novas:
                categorias_novas[brand] = {
                    "nome": brand,
                    "slug": slugify(brand),
                    "albuns": [],
                }
            categorias_novas[brand]["albuns"].append(album_entry)

            processed_count += 1
            if processed_count % BATCH_SIZE == 0:
                # Salva parcial
                data["categorias"] = list(categorias_novas.values())
                data["total_albuns"] = sum(len(c["albuns"]) for c in data["categorias"])
                data["total_imagens"] = sum(len(a["imagens"]) for c in data["categorias"] for a in c["albuns"])
                DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
                print(f"💾 Salvo parcial: {data['total_albuns']} álbuns, {data['total_imagens']} imagens")
            time.sleep(SLEEP)

    # Salva final
    data["categorias"] = sorted(
        list(categorias_novas.values()),
        key=lambda c: (-len(c["albuns"]), c["nome"])
    )
    data["total_albuns"] = sum(len(c["albuns"]) for c in data["categorias"])
    data["total_imagens"] = sum(len(a["imagens"]) for c in data["categorias"] for a in c["albuns"])
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"✅ FINAL: {len(data['categorias'])} categorias, "
          f"{data['total_albuns']} álbuns, {data['total_imagens']} imagens")

if __name__ == "__main__":
    main()
