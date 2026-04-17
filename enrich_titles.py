#!/usr/bin/env python3
"""
enrich_titles.py — Busca titulos reais dos albuns que ficaram como "Produto".
"""
import re
import json
import time
import urllib.request
import ssl
from pathlib import Path

BASE = "https://ovosneaker.x.yupoo.com"
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
    re.compile(r"\|\s*相册\s*\|", re.IGNORECASE),
    re.compile(r"\|\s*照片\s*\|", re.IGNORECASE),
]

def clean_title(raw):
    t = raw or ""
    for pat in CENSOR_PATTERNS:
        t = pat.sub("", t)
    t = t.split("|")[0]
    t = re.sub(r"^[\s\|\-–—]+", "", t)
    t = re.sub(r"[\s\|\-–—]+$", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t or "Produto"

def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
                return r.read().decode("utf-8", errors="ignore")
        except Exception:
            if i < tries - 1:
                time.sleep(2 * (i + 1))
    return ""

def get_album_title(album_id):
    url = f"{BASE}/albums/{album_id}?uid=1"
    html = fetch(url)
    if not html:
        return ""
    m = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
    if m:
        t = clean_title(m.group(1))
        if t and t != "Produto":
            return t
    m = re.search(r'<h1[^>]*>([^<]+)</h1>', html, re.IGNORECASE)
    if m:
        t = clean_title(m.group(1))
        if t and t != "Produto":
            return t
    m = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html, re.IGNORECASE)
    if m:
        t = clean_title(m.group(1))
        if t and t != "Produto":
            return t
    return ""

def main():
    if not DATA_FILE.exists():
        print("data.json nao existe")
        return
    data = json.loads(DATA_FILE.read_text())
    cats = data.get("categorias", [])
    to_enrich = []
    for cat in cats:
        for alb in cat.get("albuns", []):
            if alb.get("titulo", "").strip().lower() in ("produto", "", "album"):
                to_enrich.append((cat, alb))
    total = len(to_enrich)
    print(f"Albuns com titulo 'Produto': {total}")
    if total == 0:
        print("Nada a fazer!")
        return
    updated = 0
    for i, (cat, alb) in enumerate(to_enrich, 1):
        new_title = get_album_title(alb["id"])
        if new_title and new_title != "Produto":
            alb["titulo"] = new_title
            updated += 1
            if updated % 10 == 0 or updated <= 5:
                print(f"  [{i}/{total}] {cat['nome']} / {new_title[:60]}")
        time.sleep(0.15)
        if i % 50 == 0:
            DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
            print(f"  [progresso] salvou parcial: {updated} atualizados ate aqui")
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"\nFINAL: {updated} de {total} albuns com titulo atualizado")

if __name__ == "__main__":
    main()
