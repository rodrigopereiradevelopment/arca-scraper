import os
from pymongo import MongoClient
import ftfy
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv("MONGO_URI"))
db = client["arca_bronze"]

for item in db["produtos"].find().limit(5):
    nome = item.get("nome", "")
    print("RAW bytes:", nome.encode('utf-8'))
    print("ftfy:", ftfy.fix_text(nome))
    try:
        print("latin1->utf8:", nome.encode('latin-1').decode('utf-8'))
    except Exception as e:
        print("latin1->utf8: ERRO -", e)
    print("---")