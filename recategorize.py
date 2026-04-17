#!/usr/bin/env python3
"""
recategorize.py — Reorganiza imagens JÁ baixadas em pastas por marca.

Lê data.json antigo (se existir) com títulos dos álbuns, classifica por marca,
move imagens para images/<marca>/<album_id>/ e gera data.json novo
com estrutura {categorias: [{nome, slug, albuns: [...]}]}.

Uso: rode isso DEPOIS de atualizar o build.py mas ANTES de rodar o workflow.
Se não houver data.json antigo, baixa metadados do Yupoo novamente (sem reimages).
"""
import os
import re
import json
import time
import shutil
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://ovosneaker.x.yupoo.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": BASE_URL + "/",
}

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

def clean_title(raw):
    t = raw or ""
    for p in CENSOR_PATTERNS:
        t = p.sub("", t)
    t = re.sub(r"^[\s\|\-–—]+", "", t)
    t = re.sub(r"[\s\|\-–—]+$", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t or "Produto"

def detect_brand(title):
    t = title.lower()
    for brand, kws in BRANDS:
        for kw in kws:
            if kw in t:
                return brand
    return "Outros"

def slugify(s):
    s = s.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s or "item"

def fetch(url, retries=3):
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                return r
        except Exception as e:
            print(f"  erro: {e}")
        time.sleep(1 + i)
    return None

def get_album_title(album_id):
    """Pega título atual de um álbum."""
    r = fetch(f"{BASE_URL}/albums/{album_id}")
    if not r:
        return f"Álbum {album_id}"
    soup = BeautifulSoup(r.text, "html.parser")
    # Tenta várias fontes de título
    t = soup.find("h1")
    if t:
        return clean_title(t.get_text(strip=True))
    t = soup.find("title")
    if t:
        return clean_title(t.get_text(strip=True))
    return f"Álbum {album_id}"

def main():
    images_dir = Path("images")
    if not images_dir.exists():
        print("❌ Pasta images/ não existe. Nada pra reorganizar.")
        return

    # Lista álbuns pelo filesystem atual
    # Estrutura atual provável: images/<album_id>/*.jpg
    album_dirs = []
    for d in images_dir.iterdir():
        if not d.is_dir():
            continue
        # É um ID puro (só dígitos)?
        if d.name.isdigit():
            album_dirs.append(d)

    print(f"📁 {len(album_dirs)} álbuns encontrados no filesystem")

    if not album_dirs:
        print("⚠ Nenhum álbum no formato images/<id>/. Talvez já esteja reorganizado.")
        print("   Se quer reconstruir o data.json apenas, rode build.py direto.")
        return

    # Tenta carregar data.json antigo pra pegar títulos sem precisar baixar
    old_data = None
    if Path("data.json").exists():
        try:
            old_data = json.loads(Path("data.json").read_text())
        except Exception:
            old_data = None

    # Mapa album_id → título antigo
    old_titles = {}
    if old_data:
        # Tenta formato novo (categorias)
        if "categorias" in old_data:
            for c in old_data["categorias"]:
                for a in c.get("albuns", []):
                    old_titles[a["id"]] = a["titulo"]
        # Tenta formato antigo (lista plana)
        elif "albuns" in old_data:
            for a in old_data["albuns"]:
                old_titles[a["id"]] = a.get("titulo") or a.get("title", "")
        elif "products" in old_data:
            for a in old_data["products"]:
                old_titles[str(a.get("id"))] = a.get("title", "")

    print(f"📄 {len(old_titles)} títulos recuperados do data.json antigo")

    # Monta estrutura por marca
    categorias = {}  # nome -> {nome, slug, albuns: []}
    for ad in sorted(album_dirs):
        album_id = ad.name
        title = old_titles.get(album_id)
        if not title:
            print(f"  🌐 Buscando título de {album_id}...")
            title = get_album_title(album_id)
            time.sleep(0.5)
        title = clean_title(title)
        brand = detect_brand(title)
        brand_slug = slugify(brand)

        # Lista imagens
        imgs = sorted([f for f in ad.iterdir() if f.suffix.lower() in
                       ('.jpg', '.jpeg', '.png', '.webp')])
        if not imgs:
            continue

        # Move pasta pra images/<brand_slug>/<album_id>/
        new_dir = images_dir / brand_slug / album_id
        if ad != new_dir:
            new_dir.parent.mkdir(parents=True, exist_ok=True)
            if new_dir.exists():
                # Merge — copia tudo
                for f in ad.iterdir():
                    shutil.move(str(f), str(new_dir / f.name))
                ad.rmdir()
            else:
                shutil.move(str(ad), str(new_dir))
            imgs = sorted([f for f in new_dir.iterdir() if f.suffix.lower() in
                           ('.jpg', '.jpeg', '.png', '.webp')])

        rel_imgs = [f"images/{brand_slug}/{album_id}/{f.name}" for f in imgs]
        capa = rel_imgs[0] if rel_imgs else ""

        if brand not in categorias:
            categorias[brand] = {
                "nome": brand,
                "slug": brand_slug,
                "albuns": [],
            }
        categorias[brand]["albuns"].append({
            "id": album_id,
            "titulo": title,
            "capa": capa,
            "imagens": rel_imgs,
        })

    # Ordena categorias por tamanho (desc)
    cats_list = sorted(categorias.values(),
                       key=lambda c: (-len(c["albuns"]), c["nome"]))

    data = {
        "categorias": cats_list,
        "total_albuns": sum(len(c["albuns"]) for c in cats_list),
        "total_imagens": sum(len(a["imagens"]) for c in cats_list for a in c["albuns"]),
    }
    Path("data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"\n✅ Reorganização concluída:")
    print(f"   {len(cats_list)} categorias")
    print(f"   {data['total_albuns']} álbuns")
    print(f"   {data['total_imagens']} imagens")
    for c in cats_list:
        print(f"   · {c['nome']}: {len(c['albuns'])} álbuns")

if __name__ == "__main__":
    main()
