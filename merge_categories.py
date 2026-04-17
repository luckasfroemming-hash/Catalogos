#!/usr/bin/env python3
"""
merge_categories.py — Consolida categorias duplicadas.
"""
import re
import json
import shutil
from pathlib import Path

DATA_FILE = Path("data.json")
IMAGES_DIR = Path("images")

MERGE_MAP = {
    "J1": "Air Jordan 1",
    "J2": "Air Jordan 2",
    "J3": "Air Jordan 3",
    "J4": "Air Jordan 4",
    "J5": "Air Jordan 5",
    "J6": "Air Jordan 6",
    "J7": "Air Jordan 7",
    "J11": "Air Jordan 11",
    "J12": "Air Jordan 12",
    "J13": "Air Jordan 13",
    "AJ1": "Air Jordan 1",
    "AJ2": "Air Jordan 2",
    "AJ3": "Air Jordan 3",
    "AJ4": "Air Jordan 4",
    "AJ5": "Air Jordan 5",
    "AJ6": "Air Jordan 6",
    "AJ7": "Air Jordan 7",
    "AJ11": "Air Jordan 11",
    "AJ12": "Air Jordan 12",
    "AJ13": "Air Jordan 13",
    "J1 LOW": "Air Jordan 1",
    "J1 MID": "Air Jordan 1",
    "J1 HIGH": "Air Jordan 1",
    "J1 TRAVIS": "Air Jordan 1",
    "J1 LOW TONGXIE": "Air Jordan 1",
    "J1 MID TONGXIE": "Air Jordan 1",
    "J1 TRAVIS TONGXIE": "Air Jordan 1",
    "J4 TONGXIE": "Air Jordan 4",
    "A F 1": "Nike Air Force 1",
    "AF1": "Nike Air Force 1",
    "A-F-1": "Nike Air Force 1",
    "A F 1 TONGXIE": "Nike Air Force 1",
    "AS": "Adidas Superstar",
    "AS TONGXIE": "Adidas Superstar",
    "1V": "Louis Vuitton",
    "1V TONGXIE": "Louis Vuitton",
    "NK": "Nike",
    "NK SHOX": "Nike Shox",
    "NK SHOX TL": "Nike Shox",
    "NK SHOX TLX": "Nike Shox",
    "NK SHOX R4 SAIL TONGXIE": "Nike Shox",
    "NK MIND": "Nike Mind",
    "NK MIND 001 TONGXIE": "Nike Mind",
    "NK MIND 002 TONGXIE": "Nike Mind",
    "NK VAPORMAX": "Nike Vapormax",
    "NK CORTEZ": "Nike Cortez",
    "NK VOMERO": "Nike Vomero",
    "NK VOMERO PREMIUM": "Nike Vomero",
    "NK VOMERO V18 PLUS": "Nike Vomero",
    "NK CLASSIC CORTEZ LEATHER": "Nike Cortez",
    "NK AVA ROVER": "Nike",
    "NK JA3": "Nike",
    "NK FREE METCON 6 TONGXIE": "Nike",
    "NK REACTX REJUVEN8 TONGXIE": "Nike",
    "NK V5 RNR": "Nike",
    "NK SHOX RIDE 2": "Nike Shox",
    "NK GALAXY": "Nike",
    "DR": "Dior",
    "AD": "Adidas",
    "AD SAMBA": "Adidas Samba",
    "AD FORUM": "Adidas Forum",
    "AD SUPERSTAR": "Adidas Superstar",
    "AD CAMPUS": "Adidas Campus",
    "AD CAMPUS 00S": "Adidas Campus",
    "AD CAMPUS 00S TONGXIE": "Adidas Campus",
    "AD SAMBA TONGXIE": "Adidas Samba",
    "AD SL TONGXIE": "Adidas",
    "AD TONGXIE": "Adidas",
    "YEEZY 350": "Adidas Yeezy",
    "YEEZY 350 TONGXIE": "Adidas Yeezy",
    "YEEZY 500": "Adidas Yeezy",
    "YEEZY 700": "Adidas Yeezy",
    "YEEZY 500 700": "Adidas Yeezy",
    "YEEZY SLIDE": "Adidas Yeezy",
    "YEEZY FOAM RUNNER": "Adidas Yeezy",
    "AIR MAX 90": "Nike Air Max",
    "AIR MAX 95": "Nike Air Max",
    "AIR MAX 97": "Nike Air Max",
    "AIR MAX TN": "Nike Air Max",
    "AIR MAX PLUS": "Nike Air Max",
    "AIR MAX DN": "Nike Air Max",
    "AIR MAX DN 8": "Nike Air Max",
    "AIR MAX SCORPION": "Nike Air Max",
    "MAX": "Nike Air Max",
    "MAX 90": "Nike Air Max",
    "MAX 95": "Nike Air Max",
    "MAX 97": "Nike Air Max",
    "MAX TN": "Nike Air Max",
    "MAX PLUS": "Nike Air Max",
    "MAX DN": "Nike Air Max",
    "MAX DN 8": "Nike Air Max",
    "MAX SCORPION": "Nike Air Max",
    "MAX SCORPION FLYKNIT": "Nike Air Max",
    "AIR MORE UPTEMPO": "Nike Air More Uptempo",
    "DUNK TONGXIE": "Nike Dunk",
    "SB DUNK": "Nike SB Dunk",
    "PK": "Adidas",
    "VT": "Nike Dunk",
    "XC": "Adidas",
    "NB": "New Balance",
    "NB 550": "New Balance",
    "NB 9060": "New Balance",
    "NB 9060 TONGXIE": "New Balance",
    "NB 2002": "New Balance",
    "NB 327": "New Balance",
    "NB 327 TONGXIE": "New Balance",
    "NB MIU MIU": "New Balance",
    "NB MIU MIU TONGXIE": "New Balance",
    "UGG TONGXIE": "UGG",
    "U G G": "UGG",
    "U G G TONGXIE": "UGG",
    "CROCS TONGXIE": "Crocs",
    "CRO CS": "Crocs",
    "CRO CS TONGXIE": "Crocs",
    "PU MA": "Puma",
    "PU MA TONGXIE": "Puma",
    "KOBE": "Nike Kobe",
    "TIM BERLAND": "Timberland",
    "GGDB": "Golden Goose",
    "GGDB TONGXIE": "Golden Goose",
    "MC QUEEN": "Alexander McQueen",
    "MCQUEEN": "Alexander McQueen",
    "MC QUEEN TONGXIE": "Alexander McQueen",
    "ON CLOUD TONGXIE": "On Running",
    "ON CLOUD": "On Running",
    "VAN S": "Vans",
    "VAN S KNU SKOOL": "Vans",
    "ADI DAS": "Adidas",
    "MAI SON MAR GIELA": "Maison Margiela",
    "A MIRI": "AMIRI",
    "A-MIRI": "AMIRI",
    "MIHARA YASUHIRO": "Mihara Yasuhiro",
    "GD A MIRI": "AMIRI",
    "CAMISAS DE FUTEBOL": "Camisas de Futebol",
    "SELECCION NACIONAL": "Camisas de Futebol",
    "BAD BUNNY X AD": "Adidas",
    "BAD BUNNY": "Adidas",
    "KIDS SHOES SERIES": "Infantil",
}

def norm_key(s):
    s = (s or "").upper()
    # Substitui caracteres chineses 童鞋 (kids) por TONGXIE
    s = s.replace("童鞋", " TONGXIE")
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def slugify(s):
    s = (s or "").lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s or "item"

def main():
    if not DATA_FILE.exists():
        print("data.json nao existe")
        return
    data = json.loads(DATA_FILE.read_text())
    cats = data.get("categorias", [])
    print(f"Categorias antes: {len(cats)}")

    merge_norm = {norm_key(k): v for k, v in MERGE_MAP.items()}
    result = {}

    for cat in cats:
        nome_orig = cat.get("nome", "").strip()
        key = norm_key(nome_orig)

        if key in merge_norm:
            final_name = merge_norm[key]
        else:
            final_name = nome_orig

        if final_name not in result:
            result[final_name] = {
                "nome": final_name,
                "slug": slugify(final_name),
                "albuns": [],
            }
        existing_ids = {a["id"] for a in result[final_name]["albuns"]}
        for alb in cat.get("albuns", []):
            if alb["id"] not in existing_ids:
                new_slug = result[final_name]["slug"]
                old_slug = cat.get("slug", "")
                if old_slug and old_slug != new_slug:
                    for i, img_path in enumerate(alb.get("imagens", [])):
                        old_path = Path(img_path)
                        if old_path.exists():
                            new_path = Path("images") / new_slug / alb["id"] / old_path.name
                            new_path.parent.mkdir(parents=True, exist_ok=True)
                            try:
                                shutil.move(str(old_path), str(new_path))
                                alb["imagens"][i] = str(new_path).replace("\\", "/")
                            except Exception as e:
                                print(f"    erro movendo {old_path}: {e}")
                    if alb.get("capa"):
                        capa_path = Path(alb["capa"])
                        new_capa = Path("images") / new_slug / alb["id"] / capa_path.name
                        if new_capa.exists():
                            alb["capa"] = str(new_capa).replace("\\", "/")
                    old_album_dir = Path("images") / old_slug / alb["id"]
                    if old_album_dir.exists() and not any(old_album_dir.iterdir()):
                        old_album_dir.rmdir()

                result[final_name]["albuns"].append(alb)
                existing_ids.add(alb["id"])

        old_slug = cat.get("slug", "")
        if old_slug and old_slug != result[final_name]["slug"]:
            old_cat_dir = Path("images") / old_slug
            if old_cat_dir.exists():
                try:
                    if not any(old_cat_dir.iterdir()):
                        old_cat_dir.rmdir()
                except Exception:
                    pass

    final_cats = [c for c in result.values() if c["albuns"]]
    final_cats.sort(key=lambda c: (-len(c["albuns"]), c["nome"]))

    data["categorias"] = final_cats
    data["total_albuns"] = sum(len(c["albuns"]) for c in final_cats)
    data["total_imagens"] = sum(len(a["imagens"]) for c in final_cats for a in c["albuns"])

    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"Categorias depois: {len(final_cats)}")
    print(f"Total: {data['total_albuns']} albuns, {data['total_imagens']} imagens")
    print("\nTop 30 categorias:")
    for c in final_cats[:30]:
        print(f"  {c['nome']}: {len(c['albuns'])} albuns")

if __name__ == "__main__":
    main()
