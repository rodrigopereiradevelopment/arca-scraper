import os
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
from collections import defaultdict

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI não encontrada no .env.")

client    = MongoClient(MONGO_URI)
db_bronze = client["arca_bronze"]
db_silver = client["arca_silver"]


def truncar_data(data_raw) -> str:
    try:
        if isinstance(data_raw, datetime):
            return data_raw.strftime("%Y-%m-%d")
        return str(data_raw)[:10]
    except Exception:
        return ""


def deduplicar_historico_bronze():
    """
    Lê o histórico do bronze em Python, agrupa por id_origem+mercado+dia,
    mantém o _id mais recente e deleta os duplicados.
    """
    colecao = db_bronze["historico_precos"]
    total_antes = colecao.count_documents({})
    print(f"\n📦 arca_bronze.historico_precos")
    print(f"   Total antes: {total_antes}")

    # Agrupa em memória: chave -> (id_mais_recente, [todos_os_ids])
    grupos = defaultdict(list)

    print("   🔄 Lendo documentos...")
    for doc in colecao.find({}, {"_id": 1, "id_origem": 1, "mercado": 1, "data": 1}):
        chave = (
            str(doc.get("id_origem", "")),
            str(doc.get("mercado", "")),
            truncar_data(doc.get("data", ""))
        )
        grupos[chave].append(doc["_id"])

    # Encontra duplicatas
    ids_para_deletar = []
    for chave, ids in grupos.items():
        if len(ids) > 1:
            # Mantém o último inserido (maior ObjectId = mais recente)
            ids_sorted = sorted(ids, reverse=True)
            ids_para_deletar.extend(ids_sorted[1:])  # deleta todos menos o primeiro

    print(f"   Duplicatas encontradas: {len(ids_para_deletar)}")

    if not ids_para_deletar:
        print("   ✅ Nenhuma duplicata encontrada.")
        return

    # Deleta em lotes
    deletados = 0
    chunk = 1000
    for i in range(0, len(ids_para_deletar), chunk):
        lote = ids_para_deletar[i:i + chunk]
        resultado = colecao.delete_many({"_id": {"$in": lote}})
        deletados += resultado.deleted_count
        print(f"   🗑️  Deletados até agora: {deletados}/{len(ids_para_deletar)}")

    print(f"   Total depois: {colecao.count_documents({})}")
    print("   ✅ Concluído.")


def deduplicar_historico_silver():
    """
    Silver: data já é string YYYY-MM-DD.
    Agrupa por nome_padronizado + supermercado + data.
    """
    colecao = db_silver["historico_precos"]
    total_antes = colecao.count_documents({})
    print(f"\n📦 arca_silver.historico_precos")
    print(f"   Total antes: {total_antes}")

    grupos = defaultdict(list)

    print("   🔄 Lendo documentos...")
    for doc in colecao.find({}, {"_id": 1, "nome_padronizado": 1, "supermercado": 1, "data": 1}):
        chave = (
            str(doc.get("nome_padronizado", "")),
            str(doc.get("supermercado", "")),
            str(doc.get("data", ""))[:10]
        )
        grupos[chave].append(doc["_id"])

    ids_para_deletar = []
    for chave, ids in grupos.items():
        if len(ids) > 1:
            ids_sorted = sorted(ids, reverse=True)
            ids_para_deletar.extend(ids_sorted[1:])

    print(f"   Duplicatas encontradas: {len(ids_para_deletar)}")

    if not ids_para_deletar:
        print("   ✅ Nenhuma duplicata encontrada.")
        return

    deletados = 0
    chunk = 1000
    for i in range(0, len(ids_para_deletar), chunk):
        lote = ids_para_deletar[i:i + chunk]
        resultado = colecao.delete_many({"_id": {"$in": lote}})
        deletados += resultado.deleted_count
        print(f"   🗑️  Deletados até agora: {deletados}/{len(ids_para_deletar)}")

    print(f"   Total depois: {colecao.count_documents({})}")
    print("   ✅ Concluído.")


def deduplicar_produtos_silver():
    """
    Silver produtos: agrupa por nome_padronizado + supermercado.
    """
    colecao = db_silver["produtos"]
    total_antes = colecao.count_documents({})
    print(f"\n📦 arca_silver.produtos")
    print(f"   Total antes: {total_antes}")

    grupos = defaultdict(list)

    print("   🔄 Lendo documentos...")
    for doc in colecao.find({}, {"_id": 1, "nome_padronizado": 1, "supermercado": 1}):
        chave = (
            str(doc.get("nome_padronizado", "")),
            str(doc.get("supermercado", ""))
        )
        grupos[chave].append(doc["_id"])

    ids_para_deletar = []
    for chave, ids in grupos.items():
        if len(ids) > 1:
            ids_sorted = sorted(ids, reverse=True)
            ids_para_deletar.extend(ids_sorted[1:])

    print(f"   Duplicatas encontradas: {len(ids_para_deletar)}")

    if not ids_para_deletar:
        print("   ✅ Nenhuma duplicata encontrada.")
        return

    deletados = 0
    chunk = 1000
    for i in range(0, len(ids_para_deletar), chunk):
        lote = ids_para_deletar[i:i + chunk]
        resultado = colecao.delete_many({"_id": {"$in": lote}})
        deletados += resultado.deleted_count
        print(f"   🗑️  Deletados até agora: {deletados}/{len(ids_para_deletar)}")

    print(f"   Total depois: {colecao.count_documents({})}")
    print("   ✅ Concluído.")


if __name__ == "__main__":
    print("=" * 50)
    print("🧹 INICIANDO DEDUPLICAÇÃO")
    print("=" * 50)

    deduplicar_historico_bronze()
    deduplicar_historico_silver()
    deduplicar_produtos_silver()

    print("\n" + "=" * 50)
    print("🎉 Deduplicação concluída!")
    print("=" * 50)