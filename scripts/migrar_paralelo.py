# scripts/migrar_paralelo.py
"""
Migração paralela - igual aos scrapers!
Processa vários produtos ao mesmo tempo
Converte histórico separado (coleção historico_precos) 
para histórico embutido dentro de cada produto
"""

from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["arca_bronze"]

MAX_WORKERS = 10      # 10 processos paralelos
BATCH_SIZE = 100      # Processa 100 produtos por vez


def migrar_produto(produto):
    """Migra UM produto para o novo formato (histórico embutido)"""
    try:
        id_origem = produto.get("id_origem")
        mercado = produto.get("mercado")
        
        if not id_origem or not mercado:
            return None
        
        # Busca TODO o histórico deste produto na coleção separada
        historico = list(db.historico_precos.find({
            "id_origem": id_origem,
            "mercado": mercado
        }).sort("data", 1))
        
        if not historico:
            return None
        
        # Converte o histórico para array embutido
        historico_array = []
        total_coletas = 0
        menor_preco = None
        maior_preco = None
        
        for h in historico:
            data = h.get("data")
            preco = h.get("preco", 0)
            
            # Formata data como string YYYY-MM-DD
            if isinstance(data, datetime):
                data_str = data.strftime("%Y-%m-%d")
            else:
                data_str = str(data)[:10] if data else ""
            
            historico_array.append({
                "data": data_str,
                "preco": preco
            })
            total_coletas += 1
            
            if menor_preco is None or preco < menor_preco:
                menor_preco = preco
            if maior_preco is None or preco > maior_preco:
                maior_preco = preco
        
        # Atualiza o produto com o histórico embutido
        db.produtos.update_one(
            {"id_origem": id_origem, "mercado": mercado},
            {
                "$set": {
                    "historico_precos": historico_array,
                    "total_coletas": total_coletas,
                    "menor_preco_historico": menor_preco,
                    "maior_preco_historico": maior_preco,
                    "preco_atual": produto.get("preco"),
                    "data_ultima_coleta": produto.get("data_extracao", datetime.now())
                },
                "$unset": {
                    "preco": "",           # Remove campo antigo
                    "data_extracao": ""    # Remove campo antigo
                }
            }
        )
        return id_origem
        
    except Exception as e:
        print(f"   ❌ Erro no produto {produto.get('id_origem')}: {e}")
        return None


def main():
    print("🚀 Iniciando migração PARALELA...")
    print(f"   📌 {MAX_WORKERS} threads simultâneas")
    print(f"   📌 Batch size: {BATCH_SIZE}")
    
    # Buscar produtos que ainda não têm histórico embutido
    produtos_pendentes = list(db.produtos.find({
        "historico_precos": {"$exists": False}
    }, {
        "id_origem": 1, "mercado": 1, "preco": 1, "data_extracao": 1
    }))
    
    total_pendentes = len(produtos_pendentes)
    print(f"📊 Produtos pendentes: {total_pendentes}")
    
    if total_pendentes == 0:
        print("✅ Nenhum produto pendente!")
        return
    
    total_processados = 0
    inicio = time.time()
    
    # Processar em batches
    for i in range(0, total_pendentes, BATCH_SIZE):
        batch = produtos_pendentes[i:i+BATCH_SIZE]
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(migrar_produto, produto): produto 
                      for produto in batch}
            
            for future in as_completed(futures):
                resultado = future.result()
                if resultado:
                    total_processados += 1
        
        percentual = (total_processados / total_pendentes) * 100
        print(f"   ✅ Lote {i//BATCH_SIZE + 1}: {total_processados}/{total_pendentes} ({percentual:.1f}%)")
    
    fim = time.time()
    duracao = int(fim - inicio)
    
    print(f"\n🎉 Migração concluída!")
    print(f"📊 Total processado: {total_processados} produtos")
    print(f"⏱️ Tempo total: {duracao // 60} minutos e {duracao % 60} segundos")
    
    # Estatísticas finais
    com_historico = db.produtos.count_documents({"historico_precos": {"$exists": True, "$ne": []}})
    print(f"✅ Produtos com histórico: {com_historico}")


if __name__ == "__main__":
    main()