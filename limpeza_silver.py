import os
from pymongo import MongoClient
import re
from dotenv import load_dotenv
import ftfy

# Carrega as variáveis do arquivo .env
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError("⚠️ MONGO_URI não encontrada no arquivo .env. Verifique sua configuração.")

client = MongoClient(MONGO_URI)
db = client["arca_bronze"]          # origem (leitura)
db_silver = client["arca_silver"]   # destino (escrita)

collection_produtos = db["produtos"]
collection_historico = db["historico_precos"]

collection_silver_produtos = db_silver["produtos"]        # sem o _silver no nome
collection_silver_historico = db_silver["historico_precos"]

def corrigir_encoding(texto: str) -> str:
    if not texto:
        return ""
    return ftfy.fix_text(str(texto))

def limpar_texto(texto):
    if not texto:
        return ""
    texto_corrigido = corrigir_encoding(texto)
    texto_corrigido = texto_corrigido.replace(',', '.')  # 1,3KG → 1.3KG
    texto_limpo = re.sub(r'[^a-zA-Z0-9\s/.]', '', str(texto_corrigido))
    return " ".join(texto_limpo.split()).upper()

def padronizar_unidade(valor_str):
    if not valor_str:
        return None, 'UN'
    
    valor_str = str(valor_str).lower().strip()
    
    match_kg = re.search(r'(\d+[\.,]?\d*)\s*(kg|quilo|kilos)', valor_str)
    match_g = re.search(r'(\d+[\.,]?\d*)\s*(g|gramas)', valor_str)
    match_l = re.search(r'(\d+[\.,]?\d*)\s*(l|litro|litros)', valor_str)
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

def processar_e_salvar_mongodb():
    # 1. Processamento da coleção de Produtos
    
    collection_silver_produtos.delete_many({})
    total_produtos = collection_produtos.count_documents({})
    print(f"Processando {total_produtos} produtos...")
    
    lote_produtos = []
    chunk_size = 1000
    
    for item in collection_produtos.find():
        nome_original = item.get("nome", "")
        preco_raw = item.get("preco", 0.0)
        mercado = item.get("mercado", "Desconhecido")
        unidade_raw = item.get("unidade", "")
        ean_raw = item.get("ean", "N/A")
        categoria = item.get("categoria", "GERAL")
        url_produto = item.get("url_produto", "")
        url_imagem = item.get("url_imagem", "")
        
        qtde, unidade_medida = padronizar_unidade(unidade_raw)
        
        item_silver = {
            "nome_original": corrigir_encoding(nome_original),
            "nome_padronizado": limpar_texto(nome_original),
            "preco": limpar_preco(preco_raw),
            "supermercado": mercado,
            "unidade_medida": unidade_medida,
            "quantidade": qtde,
            "ean": ean_raw,
            "categoria": categoria,
            "url_produto": url_produto,
            "url_imagem": url_imagem
        }
        
        lote_produtos.append(item_silver)
        
        if len(lote_produtos) >= chunk_size:
            collection_silver_produtos.insert_many(lote_produtos)
            lote_produtos = []
            
    if lote_produtos:
        collection_silver_produtos.insert_many(lote_produtos)
        
    # Cria os índices para produtos
    collection_silver_produtos.create_index([("nome_padronizado", 1)])
    collection_silver_produtos.create_index([("supermercado", 1)])
    
    print("✅ Produtos processados e salvos na 'produtos_silver'.")

    # 2. Processamento da coleção de Histórico de Preços
    collection_silver_historico.delete_many({})
    total_historico = collection_historico.count_documents({})
    print(f"Processando {total_historico} registros de histórico...")
    
    lote_historico = []
    
    for item in collection_historico.find():
        nome_original = item.get("nome", "")
        preco_raw = item.get("preco", 0.0)
        mercado = item.get("mercado", "Desconhecido")
        ean_raw = item.get("ean", "N/A")
        data = item.get("data", "")
        url_produto = item.get("url_produto", "")
        
        item_hist_silver = {
            "nome_original": corrigir_encoding(nome_original),
            "nome_padronizado": limpar_texto(nome_original),
            "preco": limpar_preco(preco_raw),
            "supermercado": mercado,
            "ean": ean_raw,
            "data": data,
            "url_produto": url_produto
        }
        
        lote_historico.append(item_hist_silver)
        
        if len(lote_historico) >= chunk_size:
            collection_silver_historico.insert_many(lote_historico)
            lote_historico = []
            
    if lote_historico:
        collection_silver_historico.insert_many(lote_historico)
        
    # Cria os índices para o histórico
    collection_silver_historico.create_index([("nome_padronizado", 1)])
    collection_silver_historico.create_index([("data", -1)])
    
    print("✅ Histórico processado e salvo na 'historico_precos_silver'.")
    print("🎉 Processamento concluído com sucesso!")

if __name__ == "__main__":
    processar_e_salvar_mongodb()