import os
from pymongo import MongoClient
from dotenv import load_dotenv
import ftfy

load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["arca_bronze"]
collection = db["produtos"]

def auditar_mercados():
    print("Iniciando auditoria de codificação em todos os mercados...\n")
    
    # Agrupa a contagem de problemas por mercado
    mercados = ["GoodBom", "PagueMenos", "São Vicente", "Atacadão", "Imperial", "Ponto Novo"]
    
    for mercado in mercados:
        query = {"mercado": mercado}
        total_mercado = collection.count_documents(query)
        
        # Busca amostras com caracteres corrompidos
        problemas = 0
        for item in collection.find(query):
            nome = item.get("nome", "")
            # Verifica se o texto original possui caracteres estranhos
            if "Ã" in nome:
                problemas += 1
                
        print(f"[{mercado}] - Total analisado: {total_mercado} | Inconsistências detectadas: {problemas}")

if __name__ == "__main__":
    auditar_mercados()