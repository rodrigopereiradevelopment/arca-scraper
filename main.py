import os
from pymongo import MongoClient
from dotenv import load_dotenv

# 1. Tenta carregar o arquivo .env
load_dotenv()

def iniciar_conexao():
    # Pega a string do .env
    uri = os.getenv("MONGO_URI")
    
    # Exibe o que foi lido (ajuda a descobrir se o .env funcionou)
    print(f"🔍 DEBUG: String lida do .env: {uri}") 
    
    if not uri or "seu_usuario" in uri:
        print("❌ ERRO: A MONGO_URI não foi definida corretamente no arquivo .env")
        return None

    try:
        # 2. Configura o cliente com um tempo de espera (timeout) de 5 segundos
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        
        # 3. Testa a conexão com um comando de PING
        print("🛰️ Tentando contato com o MongoDB Atlas...")
        client.admin.command('ping')
        print("✅ CONEXÃO ESTABELECIDA COM SUCESSO!")
        
        return client
        
    except Exception as e:
        print(f"❌ ERRO DE CONEXÃO: {e}")
        print("\n💡 DICA: Verifique se o seu IP está liberado no 'Network Access' do MongoDB Atlas.")
        return None

# O ponto de partida do script
if __name__ == "__main__":
    iniciar_conexao()