# scripts/migrar_para_historico_embutido.py
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["arca_bronze"]

print("🚀 Iniciando migração para histórico embutido...")

# 1. Para cada produto, buscar seu histórico
produtos = db.produtos.find({})
total = 0

for produto in produtos:
    id_origem = produto.get("id_origem")
    mercado = produto.get("mercado")
    
    if not id_origem or not mercado:
        continue
    
    # Busca todo histórico deste produto
    historico = db.historico_precos.find({
        "id_origem": id_origem,
        "mercado": mercado
    }).sort("data", 1)  # ordena por data
    
    # Converte para array
    historico_array = []
    total_coletas = 0
    menor_preco = None
    maior_preco = None
    
    for h in historico:
        data = h.get("data")
        preco = h.get("preco")
        
        # Formata data como string YYYY-MM-DD
        if isinstance(data, datetime):
            data_str = data.strftime("%Y-%m-%d")
        else:
            data_str = str(data)[:10]
        
        historico_array.append({
            "data": data_str,
            "preco": preco
        })
        total_coletas += 1
        
        # Atualiza min/max
        if menor_preco is None or preco < menor_preco:
            menor_preco = preco
        if maior_preco is None or preco > maior_preco:
            maior_preco = preco
    
    # Atualiza o produto com o histórico embutido
    if historico_array:
        db.produtos.update_one(
            {"id_origem": id_origem, "mercado": mercado},
            {
                "$set": {
                    "historico_precos": historico_array,
                    "total_coletas": total_coletas,
                    "menor_preco_historico": menor_preco,
                    "maior_preco_historico": maior_preco,
                    "preco_atual": produto.get("preco"),  # renomeia campo
                    "data_ultima_coleta": produto.get("data_extracao", datetime.now())
                },
                "$unset": {
                    "preco": "",  # remove campo antigo
                    "data_extracao": ""  # remove campo antigo (opcional)
                }
            }
        )
        total += 1
        
        if total % 1000 == 0:
            print(f"   ✅ {total} produtos migrados...")

print(f"\n🎉 Migração concluída! {total} produtos atualizados.")

# 2. Verificar resultado
print("\n📊 Estatísticas pós-migração:")
print(f"   Produtos com histórico: {db.produtos.count_documents({'historico_precos': {'$exists': True}})}")
print(f"   Produtos sem histórico: {db.produtos.count_documents({'historico_precos': {'$exists': False}})}")

# 3. (Opcional) Backup antes de deletar
print("\n⚠️ Atenção: A coleção historico_precos ainda existe com 371k documentos.")
print("   Recomendo: esperar 1 dia, verificar se tudo funciona, depois deletar:")
print("   db.historico_precos.drop()")