import os
from pymongo import MongoClient, UpdateOne
import re
import time  # ← ADICIONADO
from datetime import datetime, timedelta  # ← timedelta adicionado
from dotenv import load_dotenv
import ftfy

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("⚠️ MONGO_URI não encontrada no arquivo .env.")

client = MongoClient(MONGO_URI)
db        = client["arca_bronze"]
db_silver = client["arca_silver"]

collection_produtos  = db["produtos"]
collection_silver_produtos  = db_silver["produtos"]
collection_silver_historico = db_silver["historico_precos"]


# ──────────────────────────────────────────────
# FUNÇÕES DE LIMPEZA
# ──────────────────────────────────────────────
def corrigir_encoding(texto: str) -> str:
    if not texto:
        return ""
    return ftfy.fix_text(str(texto))


def limpar_texto(texto):
    if not texto:
        return ""
    texto_corrigido = corrigir_encoding(texto)
    texto_corrigido = texto_corrigido.replace(',', '.')
    texto_limpo = re.sub(r'[^a-zA-Z0-9\s/.]', '', str(texto_corrigido))
    return " ".join(texto_limpo.split()).upper()


def padronizar_unidade(valor_str):
    if not valor_str:
        return None, 'UN'
    valor_str = str(valor_str).lower().strip()

    match_kg = re.search(r'(\d+[\.,]?\d*)\s*(kg|quilo|kilos)', valor_str)
    match_g  = re.search(r'(\d+[\.,]?\d*)\s*(g|gramas)', valor_str)
    match_l  = re.search(r'(\d+[\.,]?\d*)\s*(l|litro|litros)', valor_str)
    match_ml = re.search(r'(\d+[\.,]?\d*)\s*(ml|mililitros)', valor_str)

    if match_kg:
        return float(match_kg.group(1).replace(',', '.')), 'KG'
    if match_g:
        return float(match_g.group(1).replace(',', '.')), 'G'
    if match_l:
        return float(match_l.group(1).replace(',', '.')), 'L'
    if match_ml:
        return float(match_ml.group(1).replace(',', '.')), 'ML'

    return None, 'UN'


def limpar_preco(preco_str):
    if isinstance(preco_str, (int, float)):
        return float(preco_str)
    if not preco_str:
        return 0.0
    preco_str = str(preco_str).replace('R$', '').replace('$', '').strip()
    preco_str = preco_str.replace('.', '').replace(',', '.')
    try:
        return float(preco_str)
    except ValueError:
        return 0.0


# ──────────────────────────────────────────────
# PROCESSAMENTO PRINCIPAL (COM CRONÔMETRO)
# ──────────────────────────────────────────────
def processar_e_salvar_mongodb():
    inicio_limpeza = time.time()
    chunk_size = 1000
    data_hoje = datetime.now().strftime("%Y-%m-%d")

    print("=" * 40)
    print("🧹 INICIANDO LIMPEZA E PADRONIZAÇÃO (CAMADA SILVER)")
    print(f"   Início: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 40)

    # ── 1. Produtos: Bronze → Silver ──────────────────────────────────────
    inicio_prod = time.time()
    total_produtos = collection_produtos.count_documents({})
    print(f"\n📦 Processando {total_produtos:,} produtos (bronze → silver)...")

    lote_produtos = []
    historico_para_salvar = []
    inseridos = atualizados = 0
    contador = 0

    for item in collection_produtos.find():
        nome_original = item.get("nome", "")
        qtde, unidade_medida = padronizar_unidade(item.get("unidade", ""))

        nome_padronizado = limpar_texto(nome_original)
        preco_limpo = limpar_preco(item.get("preco", 0.0))
        supermercado = item.get("mercado", "Desconhecido")

        item_silver = {
            "nome_original":    corrigir_encoding(nome_original),
            "nome_padronizado": nome_padronizado,
            "preco":            preco_limpo,
            "supermercado":     supermercado,
            "unidade_medida":   unidade_medida,
            "quantidade":       qtde,
            "ean":              item.get("ean", "N/A"),
            "categoria":        item.get("categoria", "GERAL"),
            "url_produto":      item.get("url_produto", ""),
            "url_imagem":       item.get("url_imagem", ""),
            "data_extracao":    item.get("data_extracao", datetime.now()),
        }

        lote_produtos.append(UpdateOne(
            {
                "nome_padronizado": nome_padronizado,
                "supermercado":     supermercado,
            },
            {"$set": item_silver},
            upsert=True
        ))

        # Gera histórico SÓ pra esse produto (data de hoje)
        historico_para_salvar.append({
            "nome_padronizado": nome_padronizado,
            "supermercado":     supermercado,
            "preco":            preco_limpo,
            "data":             data_hoje,
        })

        contador += 1

        # Bulk write a cada chunk
        if len(lote_produtos) >= chunk_size:
            resultado = collection_silver_produtos.bulk_write(lote_produtos)
            inseridos   += resultado.upserted_count
            atualizados += resultado.modified_count
            lote_produtos = []
            
            # Progresso
            pct = (contador / total_produtos) * 100
            print(f"   🔄 {contador:,}/{total_produtos:,} ({pct:.1f}%)")

    # Último lote
    if lote_produtos:
        resultado = collection_silver_produtos.bulk_write(lote_produtos)
        inseridos   += resultado.upserted_count
        atualizados += resultado.modified_count

    duracao_prod = int(time.time() - inicio_prod)
    print(f"✅ Produtos — inseridos: {inseridos:,} | atualizados: {atualizados:,}")
    print(f"   ⏱️  Tempo: {timedelta(seconds=duracao_prod)}")

    # ── 2. Histórico ─────────────────────────────────────────────────────
    inicio_hist = time.time()
    print(f"\n📊 Salvando {len(historico_para_salvar):,} registros de histórico no silver...")

    lote_hist = []
    inseridos_hist = atualizados_hist = 0

    for h in historico_para_salvar:
        lote_hist.append(UpdateOne(
            {
                "nome_padronizado": h["nome_padronizado"],
                "supermercado":     h["supermercado"],
                "data":             h["data"],
            },
            {"$set": h},
            upsert=True
        ))

        if len(lote_hist) >= chunk_size:
            resultado = collection_silver_historico.bulk_write(lote_hist)
            inseridos_hist   += resultado.upserted_count
            atualizados_hist += resultado.modified_count
            lote_hist = []

    if lote_hist:
        resultado = collection_silver_historico.bulk_write(lote_hist)
        inseridos_hist   += resultado.upserted_count
        atualizados_hist += resultado.modified_count

    duracao_hist = int(time.time() - inicio_hist)
    print(f"✅ Histórico — inseridos: {inseridos_hist:,} | atualizados: {atualizados_hist:,}")
    print(f"   ⏱️  Tempo: {timedelta(seconds=duracao_hist)}")

    # ── 3. Índices ───────────────────────────────────────────────────────
    collection_silver_produtos.create_index([("nome_padronizado", 1)])
    collection_silver_produtos.create_index([("supermercado", 1)])
    collection_silver_historico.create_index([
        ("nome_padronizado", 1),
        ("supermercado", 1),
        ("data", 1)
    ], unique=True)

    # ── Resumo Final ─────────────────────────────────────────────────────
    duracao_total = int(time.time() - inicio_limpeza)
    print("\n" + "=" * 40)
    print("📊 RESUMO DA LIMPEZA SILVER")
    print("=" * 40)
    print(f"   Produtos:   {timedelta(seconds=duracao_prod)}")
    print(f"   Histórico:  {timedelta(seconds=duracao_hist)}")
    print(f"   TOTAL:      {timedelta(seconds=duracao_total)}")
    print("=" * 40)
    print("🎉 Processamento concluído com sucesso!")


if __name__ == "__main__":
    processar_e_salvar_mongodb()