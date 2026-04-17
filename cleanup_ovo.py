#!/usr/bin/env python3
import json
import shutil
from pathlib import Path

DATA_FILE = Path("data.json")
IMAGES_DIR = Path("images")
REMOVE = ["ovo spreadsheet", "ovospreadsheet", "spreadsheet"]

def main():
    if not DATA_FILE.exists():
        print("data.json nao existe")
        return
    data = json.loads(DATA_FILE.read_text())
    cats = data.get("categorias", [])
    print(f"Categorias atuais: {len(cats)}")
    kept = []
    removed = []
    for cat in cats:
        nome_low = cat.get("nome", "").lower()
        if any(r in nome_low for r in REMOVE):
            removed.append(cat)
        else:
            kept.append(cat)
    if not removed:
        print("Nenhuma categoria a remover encontrada")
        return
    print(f"Removendo {len(removed)} categoria(s):")
    for r in removed:
        print(f"  - {r['nome']} ({len(r.get('albuns', []))} albuns)")
        slug = r.get("slug", "")
        if slug:
            folder = IMAGES_DIR / slug
            if folder.exists():
                shutil.rmtree(folder)
                print(f"    pasta images/{slug}/ deletada")
    data["categorias"] = kept
    data["total_albuns"] = sum(len(c["albuns"]) for c in kept)
    data["total_imagens"] = sum(len(a["imagens"]) for c in kept for a in c["albuns"])
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"\nAtualizado: {len(kept)} categorias, {data['total_albuns']} albuns, {data['total_imagens']} imagens")

if __name__ == "__main__":
    main()
