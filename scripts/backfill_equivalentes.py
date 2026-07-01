"""
Backfill completo da tabela produtos_equivalentes.
Processa por categoria, 1 produto por vez (uso do índice GIN é rápido).

Uso: python scripts/backfill_equivalentes.py [--categoria ID]
"""
import os
import sys
import json
import time
import argparse
import requests
from datetime import datetime

SUPABASE_URL = os.getenv("SUPABASE_MANAGEMENT_URL")
SUPABASE_KEY = os.getenv("SUPABASE_MANAGEMENT_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    sys.exit("❌ Defina SUPABASE_MANAGEMENT_URL e SUPABASE_MANAGEMENT_KEY no .env")

HEADERS = {
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

def run_sql(sql: str, label: str = "") -> list:
    """Executa SQL via Management API"""
    try:
        resp = requests.post(SUPABASE_URL, json={"query": sql}, headers=HEADERS, timeout=60)
        if resp.status_code == 201 or resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and "message" in data:
                print(f"  ERRO [{label}]: {data['message']}")
                return []
            return data if isinstance(data, list) else [data]
        else:
            print(f"  ERRO HTTP {resp.status_code} [{label}]: {resp.text[:200]}")
            return []
    except Exception as e:
        print(f"  ERRO [{label}]: {e}")
        return []

def get_categorias():
    rows = run_sql("SELECT id, nome FROM categorias ORDER BY id", "categorias")
    return [(r["id"], r["nome"]) for r in rows]

def get_produtos_por_categoria(cat_id: int):
    rows = []
    offset = 0
    while True:
        sql = f"SELECT id, nome, marca, categoria_id FROM produtos WHERE categoria_id = {cat_id} ORDER BY id LIMIT 1000 OFFSET {offset}"
        r = run_sql(sql, f"produtos cat{cat_id} off{offset}")
        if not r:
            break
        rows.extend(r)
        offset += 1000
        if len(r) < 1000:
            break
    return rows

def backfill_categoria(cat_id: int, nome_cat: str) -> tuple:
    produtos = get_produtos_por_categoria(cat_id)
    total = len(produtos)
    print(f"\n{'='*60}")
    print(f"📂 Categoria {cat_id}: {nome_cat} — {total} produtos")
    print(f"{'='*60}")

    insert_count = 0
    skip_count = 0
    start = time.time()

    for idx, p in enumerate(produtos):
        pid = p["id"]
        pnome = p["nome"]
        pmarca = p.get("marca") or ""

        pnome_esc = pnome.replace("'", "''")
        pmarca_esc = pmarca.replace("'", "''")
        marca_cond = f"CASE WHEN '{pmarca_esc}' = s.marca AND '{pmarca_esc}' != '' AND '{pmarca_esc}' != 'N/A' THEN 0.3 ELSE 0 END"

        sql = f"""
        INSERT INTO produtos_equivalentes (produto_id_a, produto_id_b, score, metodo)
        SELECT {pid}, s.id,
          GREATEST(similarity('{pnome_esc}', s.nome) * 0.5 +
            {marca_cond} +
            CASE WHEN {cat_id} = s.categoria_id THEN 0.2 ELSE 0.1 END, 0)::real,
          'trigram'
        FROM (
          SELECT id, nome, marca, categoria_id
          FROM produtos
          WHERE nome % '{pnome_esc}' AND id <> {pid}
            AND categoria_id = {cat_id}
          ORDER BY similarity(nome, '{pnome_esc}') DESC
          LIMIT 20
        ) s
        WHERE GREATEST(similarity('{pnome_esc}', s.nome) * 0.5 +
          {marca_cond} +
          CASE WHEN {cat_id} = s.categoria_id THEN 0.2 ELSE 0.1 END, 0) >= 0.30
        ON CONFLICT DO NOTHING
        """

        run_sql(sql, f"prod {pid}")

        if (idx + 1) % 100 == 0 or idx == total - 1:
            elapsed = time.time() - start
            rate = (idx + 1) / elapsed if elapsed > 0 else 0
            print(f"  [{idx+1}/{total}] {rate:.1f} prod/s")

    elapsed = time.time() - start
    print(f"  ✅ Categoria {nome_cat}: {total} produtos em {elapsed:.1f}s ({total/elapsed:.1f} prod/s)")
    return (total, insert_count)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--categoria", type=int, help="Apenas uma categoria específica")
    args = parser.parse_args()

    categorias = get_categorias()
    print(f"📊 {len(categorias)} categorias encontradas")

    total_prod = 0
    total_ins = 0
    overall_start = time.time()

    for cat_id, nome_cat in categorias:
        if args.categoria and cat_id != args.categoria:
            continue
        p, i = backfill_categoria(cat_id, nome_cat)
        total_prod += p
        total_ins += i

    overall = time.time() - overall_start
    print(f"\n{'='*60}")
    print(f"🏁 BACKFILL CONCLUÍDO")
    print(f"   Produtos: {total_prod}")
    print(f"   Tempo: {overall:.1f}s")
    print(f"{'='*60}")
