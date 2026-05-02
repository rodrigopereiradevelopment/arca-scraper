import os
from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8']

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

    def salvar_historico(self, db, batch_h: list):
        """Salva histórico com upsert por dia — evita duplicatas."""
        if not batch_h:
            return
        ops = []
        for h in batch_h:
            data_raw = h.get("data", datetime.now())
            if isinstance(data_raw, datetime):
                data_dia = data_raw.strftime("%Y-%m-%d")
            else:
                data_dia = str(data_raw)[:10]
            ops.append(UpdateOne(
                {
                    "id_origem": h.get("id_origem"),
                    "mercado":   h.get("mercado"),
                    "data":      data_dia,
                },
                {"$set": {**h, "data": data_dia}},
                upsert=True
            ))
        db['historico_precos'].bulk_write(ops)