# limpar_produtos_obsoletos.py
"""
Remove produtos que não estão no novo padrão (sem historico_precos)
"""

from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["arca_bronze"]

# Ver quantos serão deletados
count = db.produtos.count_documents({"historico_precos": {"$exists": False}})
print(f"📊 Produtos a serem deletados: {count}")

if count > 0:
    confirm = input(f"⚠️ Confirmar exclusão de {count} produtos? (s/N): ")
    if confirm.lower() == 's':
        result = db.produtos.delete_many({"historico_precos": {"$exists": False}})
        print(f"✅ Deletados: {result.deleted_count} produtos")
    else:
        print("❌ Operação cancelada")
else:
    print("✅ Nenhum produto obsoleto encontrado")