import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Carrega as variáveis do .env
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["arca_bronze"]
collection = db["produtos"]

def verificar_problemas_nome():
    # Filtra apenas produtos do GoodBom
    query = {"mercado": "GoodBom"}
    total_goodbom = collection.count_documents(query)
    
    print(f"Analisando {total_goodbom} produtos do GoodBom...")
    
    # Expressão regular para buscar caracteres acidentais típicos de erro de encoding
    problemas = []
    
    for item in collection.find(query):
        nome = item.get("nome", "")
        # Se contiver os caracteres estranhos de corrupção
        if "Ã" in nome or "" in nome:
            problemas.append({
                "id_mongo": str(item["_id"]),
                "nome_original": nome,
                "url": item.get("url_produto", "N/A")
            })
            
    # Mostra os 10 primeiros para análise
    print(f"\nForam encontrados {len(problemas)} produtos com nomes possivelmente corrompidos.")
    print("\n--- Amostra de Produtos com Nomes Incorretos ---")
    for i, p in enumerate(problemas[:10]):
        print(f"{i+1}. ID: {p['id_mongo']}")
        print(f"   Nome: {p['nome_original']}")
        print(f"   URL:  {p['url']}")
        print("-" * 50)

if __name__ == "__main__":
    verificar_problemas_nome()