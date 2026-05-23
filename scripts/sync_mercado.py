"""
Sync de UM mercado específico para o Supabase
Executado em paralelo pelo GitHub Actions
"""

import os
import argparse
from datetime import datetime
from pymongo import MongoClient
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

MERCADO_IDS = {
    "atacadao": 4,
    "sao_vicente": 6,
    "pague_menos": 5,
    "ponto_novo": 2,
    "imperial": 1,
    "goodbom": 3,
}

CATEGORIA_IDS = {
    "acougue": 2,
    "bebidas": 3,
    "frios e laticinios": 1,
    "hortifruti": 6,
    "higiene e beleza": 4,
    "limpeza": 4,
    "mercearia": 7,
    "padaria": 5,
    "congelados": 8,
    "bazar": 9,
}


def sync_mercado(mercado_nome: str):
    mercado_display = {
        "atacadao": "Atacadão",
        "sao_vicente": "São Vicente",
        "pague_menos": "Pague Menos",
        "ponto_novo": "Ponto Novo",
        "imperial": "Imperial",
        "goodbom": "GoodBom",
    }.get(mercado_nome, mercado_nome)

    print(f"🔄 Sincronizando mercado: {mercado_display}")

    mongo_client = MongoClient(os.getenv("MONGO_URI"))
    db = mongo_client["arca_bronze"]
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY")
    )

    supermercado_id = MERCADO_IDS.get(mercado_nome)
    if not supermercado_id:
        print(f"❌ Mercado desconhecido: {mercado_nome}")
        return

    produtos = list(db.produtos.find({
        "mercado": {"$regex": mercado_display, "$options": "i"}
    }))

    print(f"📦 {len(produtos)} produtos encontrados")

    inseridos = 0
    for produto in produtos:
        try:
            categoria = produto.get("categoria", "").lower()
            categoria_id = None
            for key, value in CATEGORIA_IDS.items():
                if key in categoria:
                    categoria_id = value
                    break

            produto_data = {
                "nome": produto.get("nome_normalizado"),
                "marca": produto.get("marca", "N/A"),
                "codigo_barras": produto.get("ean") if len(produto.get("ean", "")) in [8, 13] else None,
                "imagem_url": produto.get("url_imagem"),
                "categoria_id": categoria_id,
                "ativo": True,
            }

            result = supabase.table("produtos").upsert(
                produto_data,
                on_conflict="nome"
            ).execute()

            if result.data:
                produto_id = result.data[0]["id"]

                hoje = datetime.now().strftime("%Y-%m-%d")
                ja_existe = supabase.table("precos")\
                    .select("id")\
                    .eq("produto_id", produto_id)\
                    .eq("supermercado_id", supermercado_id)\
                    .gte("data_coleta", f"{hoje}T00:00:00")\
                    .maybe_single()\
                    .execute()

                if not ja_existe.data:
                    preco_data = {
                        "preco": produto.get("preco_atual"),
                        "data_coleta": produto.get("data_ultima_coleta").isoformat() if produto.get("data_ultima_coleta") else datetime.now().isoformat(),
                        "produto_id": produto_id,
                        "supermercado_id": supermercado_id,
                        "fonte_dados": "scraping",
                    }
                    supabase.table("precos").insert(preco_data).execute()
                    inseridos += 1

        except Exception as e:
            print(f"   ⚠️ Erro: {e}")

    print(f"✅ {inseridos}/{len(produtos)} produtos sincronizados")
    mongo_client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mercado", required=True)
    args = parser.parse_args()
    sync_mercado(args.mercado)