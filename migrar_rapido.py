# migrar_rapido.py
"""
Migração rápida - Processa em BATCH (100 produtos por vez)
Deve levar ~10-15 minutos para 55k produtos
"""

from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["arca_bronze"]

print("🚀 Iniciando migração RÁPIDA (modo batch)...")

# 1. Buscar todos os produtos que NÃO têm histórico embutido
produtos_pendentes = list(db.produtos.find({
    "historico_precos": {"$exists": False}
}, {
    "id_origem": 1, 
    "mercado": 1, 
    "preco": 1, 
    "data_extracao": 1,
    "nome_normalizado": 1
}))

total_pendentes = len(produtos_pendentes)
print(f"📊 Produtos pendentes: {total_pendentes}")

if total_pendentes == 0:
    print("✅ Nenhum produto pendente!")
    exit()

# 2. Processar em BATCHES
BATCH_SIZE = 100
total_processados = 0

for i in range(0, total_pendentes, BATCH_SIZE):
    batch = produtos_pendentes[i:i+BATCH_SIZE]
    print(f"🔄 Processando lote {i//BATCH_SIZE + 1}/{(total_pendentes//BATCH_SIZE)+1}...")
    
    for produto in batch:
        id_origem = produto.get("id_origem")
        mercado = produto.get("mercado")
        
        if not id_origem or not mercado:
            continue
        
        # Buscar histórico deste produto
        historico = list(db.historico_precos.find({
            "id_origem": id_origem,
            "mercado": mercado
        }, {"_id": 0, "data": 1, "preco": 1}).sort("data", 1))
        
        if not historico:
            continue
        
        # Calcular métricas
        historico_embutido = []
        total_coletas = 0
        menor_preco = None
        maior_preco = None
        
        for h in historico:
            data = h.get("data")
            preco = h.get("preco", 0)
            
            if isinstance(data, datetime):
                data_str = data.strftime("%Y-%m-%d")
            else:
                data_str = str(data)[:10] if data else ""
            
            historico_embutido.append({"data": data_str, "preco": preco})
            total_coletas += 1
            
            if menor_preco is None or preco < menor_preco:
                menor_preco = preco
            if maior_preco is None or preco > maior_preco:
                maior_preco = preco
        
        # Atualizar produto
        db.produtos.update_one(
            {"id_origem": id_origem, "mercado": mercado},
            {
                "$set": {
                    "historico_precos": historico_embutido,
                    "total_coletas": total_coletas,
                    "menor_preco_historico": menor_preco,
                    "maior_preco_historico": maior_preco,
                    "preco_atual": produto.get("preco"),
                    "data_ultima_coleta": produto.get("data_extracao", datetime.now())
                }
            }
        )
        total_processados += 1
    
    print(f"   ✅ Lote {i//BATCH_SIZE + 1} concluído. Total: {total_processados}/{total_pendentes}")

# 3. Remover campo antigo "preco" (opcional)
print("\n🧹 Limpando campos antigos...")
db.produtos.update_many(
    {"preco": {"$exists": True}},
    {"$unset": {"preco": ""}}
)

print("\n🎉 Migração concluída!")
print(f"📊 Total processado: {total_processados} produtos")
print(f"📊 Total no banco: {db.produtos.count_documents({})} produtos")

# 4. Estatísticas finais
com_historico = db.produtos.count_documents({"historico_precos": {"$exists": True, "$ne": []}})
print(f"✅ Produtos com histórico: {com_historico}")

client.close()