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

# Carrega o .env da raiz
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

MERCADO_IDS = {
    "atacadao": 4,
    "sao_vicente": 6,
    "pague_menos": 5,
    "ponto_novo": 2,
    "imperial": 1,
    "goodbom": 3,
}

# Nome exato como está salvo no MongoDB
MERCADO_DISPLAY = {
    "atacadao": "Atacadão",
    "sao_vicente": "São Vicente",
    "pague_menos": "PagueMenos",
    "ponto_novo": "Ponto Novo",
    "imperial": "Imperial",
    "goodbom": "GoodBom",
}

CATEGORIA_IDS = {
    "acougue": 2,
    "bebidas": 3,
    "frios e laticinios": 1,
    "frios laticinios": 1,
    "frios": 1,
    "hortifruti": 6,
    "hortifrutigranjeiro": 6,
    "higiene e beleza": 4,
    "higiene beleza": 4,
    "higiene": 4,
    "limpeza": 4,
    "mercearia": 7,
    "padaria": 5,
    "congelados": 8,
    "bazar": 9,
    "magazine": 9,
    "pet shop": 4,
    "mundo pet": 4,
    "peixaria": 2,
    "carnes aves peixes": 2,
    "carnes": 2,
}


def normalizar_categoria(categoria: str, nome: str = "") -> int | None:
    if not categoria:
        return None

    # Override por nome do produto
    nome_upper = nome.upper() if nome else ""
    if nome_upper:
        if re.search(r'\b(ARROZ|FEIJÃO|FEIJAO|FARINHA|AÇÚCAR|ACUCAR|CAFÉ|CAFE|MACARRÃO|MACARRAO|FUBÁ|FUBA|LENTILHA)\b', nome_upper):
            return 7
        if re.search(r'\b(LEITE|QUEIJO|MANTEIGA|IOGURTE|MUÇARELA|MUCARELA|RICOTA)\b', nome_upper):
            return 1
        if re.search(r'\b(CARNE|FRANGO|PEIXE|PICANHA|LINGUIÇA|LINGUICA|SALSICHA)\b', nome_upper):
            return 2
        if re.search(r'\b(SABÃO|SABAO|SABONETE|DETERGENTE|SHAMPOO|CONDICIONADOR|ALVEJANTE|DESINFETANTE|LIMPADOR|FRALDA|PAPEL HIGIÊNICO|PAPEL HIGIENICO)\b', nome_upper):
            return 4
        if re.search(r'\b(BANANA|MAÇÃ|MAÇA|LARANJA|TOMATE|CEBOLA|BATATA|ALFACE)\b', nome_upper):
            return 6

    cat = categoria.lower().strip()
    for key, value in CATEGORIA_IDS.items():
        if key in cat:
            return value
    return None


def upsert_produto(supabase, produto_data: dict):
    """Tenta upsert com EAN, se der conflito de barcode tenta sem."""
    try:
        result = supabase.table("produtos").upsert(
            produto_data, on_conflict="nome"
        ).execute()
        if result and result.data:
            return result.data[0]["id"]
    except Exception:
        pass

    # Tenta sem codigo_barras
    try:
        produto_data["codigo_barras"] = None
        result = supabase.table("produtos").upsert(
            produto_data, on_conflict="nome"
        ).execute()
        if result and result.data:
            return result.data[0]["id"]
    except Exception as e:
        print(f"   ⚠️ Erro no upsert: {e}")

    return None


def sync_mercado(mercado_nome: str):
    mercado_display = MERCADO_DISPLAY.get(mercado_nome, mercado_nome)
    supermercado_id = MERCADO_IDS.get(mercado_nome)

    if not supermercado_id:
        print(f"❌ Mercado desconhecido: {mercado_nome}")
        return

    print(f"🔄 Sincronizando: {mercado_display} (ID: {supermercado_id})")

    mongo_client = MongoClient(os.getenv("MONGO_URI"))
    db = mongo_client["arca_bronze"]
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY")
    )

    produtos = list(db.produtos.find({
        "mercado": {"$regex": mercado_display, "$options": "i"}
    }))

    print(f"📦 {len(produtos)} produtos encontrados no MongoDB")

    inseridos = 0
    ignorados = 0
    erros = 0
    lote_precos = []

    hoje = datetime.now().strftime("%Y-%m-%d")

    for produto in produtos:
        try:
            preco = produto.get("preco_atual") or produto.get("preco")
            if not preco:
                ignorados += 1
                continue

            nome = produto.get("nome_normalizado") or produto.get("nome")
            if not nome:
                ignorados += 1
                continue

            categoria_id = normalizar_categoria(produto.get("categoria", ""), nome)
            ean = produto.get("ean", "")
            codigo_barras = (
                ean if isinstance(ean, str)
                and len(ean) in [8, 13]
                and ean.isdigit()
                else None
            )

            produto_data = {
                "nome": nome,
                "marca": produto.get("marca", "N/A"),
                "codigo_barras": codigo_barras,
                "imagem_url": produto.get("url_imagem"),
                "categoria_id": categoria_id,
                "ativo": True,
            }

            produto_id = upsert_produto(supabase, produto_data)
            if not produto_id:
                erros += 1
                continue

            # Verifica duplicata do dia
            ja_existe = supabase.table("precos") \
                .select("id") \
                .eq("produto_id", produto_id) \
                .eq("supermercado_id", supermercado_id) \
                .gte("data_coleta", f"{hoje}T00:00:00") \
                .maybe_single() \
                .execute()

            if ja_existe and ja_existe.data:
                ignorados += 1
                continue

            data_coleta = produto.get("data_ultima_coleta") or produto.get("data_extracao")
            if isinstance(data_coleta, datetime):
                data_coleta_str = data_coleta.isoformat()
            else:
                data_coleta_str = datetime.now().isoformat()

            lote_precos.append({
                "preco": float(preco),
                "data_coleta": data_coleta_str,
                "produto_id": produto_id,
                "supermercado_id": supermercado_id,
                "fonte_dados": "scraping",
                "promocao": False,
            })

            # Insere quando atingir 250
            if len(lote_precos) >= 250:
                supabase.table("precos").insert(lote_precos).execute()
                inseridos += len(lote_precos)
                lote_precos = []
                print(f"   📤 Lote inserido — total até agora: {inseridos}")

        except Exception as e:
            print(f"   ⚠️ Erro no produto: {e}")
            erros += 1

    # Insere o restante
    if lote_precos:
        supabase.table("precos").insert(lote_precos).execute()
        inseridos += len(lote_precos)
        print(f"   📤 Último lote inserido: {len(lote_precos)}")

    print(f"\n📊 Resultado {mercado_display}:")
    print(f"   ✅ Inseridos:  {inseridos}")
    print(f"   ⏭️  Ignorados:  {ignorados}")
    print(f"   ❌ Erros:      {erros}")
    print(f"   📦 Total:      {len(produtos)}")

    mongo_client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mercado", required=True,
                        choices=list(MERCADO_IDS.keys()),
                        help="Mercado a sincronizar")
    args = parser.parse_args()
    sync_mercado(args.mercado)