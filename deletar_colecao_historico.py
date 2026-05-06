# deletar_colecao_historico.py
"""
Remove a coleção antiga de histórico (liberar espaço)
SÓ RODAR DEPOIS DE CONFIRMAR QUE A MIGRAÇÃO FUNCIONOU!
"""

from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["arca_bronze"]

# Verificar se a coleção existe
if "historico_precos" in db.list_collection_names():
    count = db.historico_precos.count_documents({})
    print(f"📊 Registros na coleção historico_precos: {count}")
    
    confirm = input(f"⚠️ Confirmar exclusão da coleção historico_precos? (s/N): ")
    if confirm.lower() == 's':
        db.historico_precos.drop()
        print("✅ Coleção historico_precos deletada com sucesso!")
        print(f"💾 Espaço liberado: ~{count * 0.2:.1f} MB estimados")
    else:
        print("❌ Operação cancelada")
else:
    print("✅ Coleção historico_precos já não existe")