import os
from pymongo import MongoClient
from dotenv import load_dotenv
from pathlib import Path

import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8'] # Usa o DNS do Google

# Busca o .env na raiz (um nível acima da pasta scrapers)
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class BaseScraper:
    def __init__(self):
        self.uri = os.getenv("MONGO_URI")
        self.client = None
        self.db = None

    def conectar(self):
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.db = self.client['arca_bronze']
            return self.db
        except Exception as e:
            print(f"❌ Erro de conexão no BaseScraper: {e}")
            return None

    def salvar_dados(self, colecao, dados):
        """Salva uma lista de produtos no MongoDB"""
        if self.db is not None:
            self.db[colecao].insert_many(dados)
            print(f"✅ {len(dados)} produtos salvos na coleção {colecao}!")