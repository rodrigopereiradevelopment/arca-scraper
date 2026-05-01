# deletar_silver_bronze.py
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv("MONGO_URI"))
db = client["arca_bronze"]

db["produtos_silver"].drop()
db["historico_precos_silver"].drop()

print("✅ Coleções antigas removidas do arca_bronze.")