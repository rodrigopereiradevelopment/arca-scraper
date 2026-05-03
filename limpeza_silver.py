import os
import time
import re
from datetime import datetime, timedelta
from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv
import ftfy

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("⚠️ MONGO_URI não encontrada no arquivo .env.")

client = MongoClient(MONGO_URI)
db_bronze = client["arca_bronze"]
db_silver = client["arca_silver"]

col_bronze_prod = db_bronze["produtos"]
col_silver_prod = db_silver["produtos"]
col_silver_hist = db_silver["historico_precos"]


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


def padronizar_unidade(texto_busca):
    """
    Extrai quantidade e unidade do TEXTO (nome do produto).
    Ex: 'ARROZ 5KG' → (5.0, 'KG')
    """
    if not texto_busca:
        return None, 'UN'
    
    t = str(texto_busca).lower().strip()
    
    match_kg = re.search(r'(\d+[\.,]?\d*)\s*(kg|quilo|kilos)', t)
    match_g  = re.search(r'(\d+[\.,]?\d*)\s*(g|gramas)', t)
    match_l  = re.search(r'(\d+[\.,]?\d*)\s*(l|litro|litros)', t)
    match_ml = re.search(r'(\d+[\.,]?\d*)\s*(ml|mililitros)', t)

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


def processar_e_salvar_mongodb():
    inicio_geral = time.time()
    chunk_size = 1000
    data_hoje = datetime.now().strftime("%Y-%m-%d")

    print("=" * 40)
    print("🧹 INICIANDO LIMPEZA E PADRONIZAÇÃO (CAMADA SILVER)")
    print(f"   Início: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 40)

    # ─── 1. ÍNDICES CRIADOS ANTES (evita lentidão no upsert) ───
    print("📇 Criando/verificando índices...")
    col_silver_prod.create_index([("nome_padronizado", 1), ("supermercado", 1)])
    col_silver_hist.create_index(
        [("nome_padronizado", 1), ("supermercado", 1), ("data", 1)],
        unique=True
    )

    # ─── 2. PROCESSAMENTO ───
    total_bronze = col_bronze_prod.count_documents({})
    print(f"📦 Processando {total_bronze:,} produtos (bronze → silver)...")

    lote_prod = []
    lote_hist = []
    processados = 0
    inseridos = atualizados = 0
    inseridos_hist = atualizados_hist = 0

    # batch_size evita carregar tudo na memória de uma vez
    for item in col_bronze_prod.find().batch_size(chunk_size):
        nome_original = item.get("nome", "")
        
        # Busca unidade no NOME (campo 'unidade' geralmente é a cidade)
        nome_para_unidade = item.get("unidade") or nome_original
        qtde, und = padronizar_unidade(nome_para_unidade)

        nome_padronizado = limpar_texto(nome_original)
        preco_limpo = limpar_preco(item.get("preco", 0.0))
        supermercado = item.get("mercado", "Desconhecido")

        doc_silver = {
            "nome_original":    corrigir_encoding(nome_original),
            "nome_padronizado": nome_padronizado,
            "preco":            preco_limpo,
            "supermercado":     supermercado,
            "unidade_medida":   und,
            "quantidade":       qtde,
            "ean":              item.get("ean", "N/A"),
            "categoria":        item.get("categoria", "GERAL"),
            "url_produto":      item.get("url_produto", ""),
            "url_imagem":       item.get("url_imagem", ""),
            "data_extracao":    item.get("data_extracao", datetime.now()),
        }

        lote_prod.append(UpdateOne(
            {"nome_padronizado": nome_padronizado, "supermercado": supermercado},
            {"$set": doc_silver},
            upsert=True
        ))

        lote_hist.append(UpdateOne(
            {"nome_padronizado": nome_padronizado, "supermercado": supermercado, "data": data_hoje},
            {"$set": {"preco": preco_limpo, "data": data_hoje}},
            upsert=True
        ))

        processados += 1

        # Bulk write a cada chunk → libera memória
        if len(lote_prod) >= chunk_size:
            r1 = col_silver_prod.bulk_write(lote_prod)
            r2 = col_silver_hist.bulk_write(lote_hist)
            inseridos += r1.upserted_count
            atualizados += r1.modified_count
            inseridos_hist += r2.upserted_count
            atualizados_hist += r2.modified_count
            lote_prod, lote_hist = [], []
            
            pct = (processados / total_bronze) * 100
            print(f"   🔄 {processados:,}/{total_bronze:,} ({pct:.1f}%)")

    # Último lote
    if lote_prod:
        r1 = col_silver_prod.bulk_write(lote_prod)
        r2 = col_silver_hist.bulk_write(lote_hist)
        inseridos += r1.upserted_count
        atualizados += r1.modified_count
        inseridos_hist += r2.upserted_count
        atualizados_hist += r2.modified_count

    duracao_total = int(time.time() - inicio_geral)

    print(f"\n✅ Produtos — inseridos: {inseridos:,} | atualizados: {atualizados:,}")
    print(f"✅ Histórico — inseridos: {inseridos_hist:,} | atualizados: {atualizados_hist:,}")

    print("\n" + "=" * 40)
    print("📊 RESUMO DA LIMPEZA SILVER")
    print("=" * 40)
    print(f"   TOTAL:      {timedelta(seconds=duracao_total)}")
    print("=" * 40)
    print("🎉 Processamento concluído com sucesso!")


if __name__ == "__main__":
    processar_e_salvar_mongodb()