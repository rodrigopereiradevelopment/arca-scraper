import os
import re
import unicodedata
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
    """
    Classe base para todos os scrapers do Projeto ARCA.
    
    Centraliza:
    - Conexão com MongoDB (arca_bronze)
    - Normalização de nomes
    - Schema padrão de produto com HISTÓRICO EMBUTIDO
    """
    
    # ──────────────────────────────────────────────
    # CONSTRUTOR E CONEXÃO
    # ──────────────────────────────────────────────
    def __init__(self):
        self.uri = os.getenv("MONGO_URI")
        self.client = None
        self.db = None

    def conectar(self):
        """Conecta ao MongoDB e retorna o banco arca_bronze"""
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.db = self.client['arca_bronze']
            # Criar índices para performance
            self._criar_indices()
            return self.db
        except Exception as e:
            print(f"❌ Erro de conexão no BaseScraper: {e}")
            return None

    def _criar_indices(self):
        """Cria índices necessários para performance"""
        try:
            self.db['produtos'].create_index([("id_origem", 1), ("mercado", 1)], unique=True)
            self.db['produtos'].create_index([("nome_normalizado", 1), ("mercado", 1)])
            print("📇 Índices verificados/criados com sucesso")
        except Exception as e:
            print(f"⚠️ Atenção: Erro ao criar índices: {e}")

    # ──────────────────────────────────────────────
    # NORMALIZADOR CENTRALIZADO
    # ──────────────────────────────────────────────
    @staticmethod
    def normalizar_nome(nome):
        """Normaliza nome de produto para comparação entre mercados"""
        if not nome:
            return "N/A"
        nome = unicodedata.normalize('NFKD', str(nome))
        nome = ''.join(c for c in nome if not unicodedata.combining(c))
        return re.sub(r'\s+', ' ', nome).strip().upper()

    # ──────────────────────────────────────────────
    # CRIAÇÃO DE DOCUMENTO PADRONIZADO (com histórico vazio)
    # ──────────────────────────────────────────────
    @classmethod
    def criar_produto(cls, **kwargs):
        """
        Cria um documento de produto com histórico embutido vazio.
        """
        defaults = {
            "id_origem":        kwargs.get("id_origem", ""),
            "ean":              kwargs.get("ean", "N/A"),
            "nome":             str(kwargs.get("nome", "N/A")).upper(),
            "nome_normalizado": cls.normalizar_nome(kwargs.get("nome", "")),
            "marca":            kwargs.get("marca", "N/A"),
            "categoria":        kwargs.get("categoria", ""),
            "subcategoria":     kwargs.get("subcategoria", ""),
            "preco_atual":      float(kwargs.get("preco", 0)),
            "preco_original":   kwargs.get("preco_original", None),
            "mercado":          kwargs.get("mercado", ""),
            "unidade":          kwargs.get("unidade", ""),
            "url_imagem":       kwargs.get("url_imagem", ""),
            "url_produto":      kwargs.get("url_produto", ""),
            "is_kg":            int(kwargs.get("is_kg", 0)),
            "data_ultima_coleta": kwargs.get("data_extracao", datetime.now()),
            "status":           kwargs.get("status", "bronze"),
            # NOVOS CAMPOS
            "historico_precos": [],
            "total_coletas":    0,
            "menor_preco_historico": None,
            "maior_preco_historico": None,
        }
        
        return defaults

    # ──────────────────────────────────────────────
    # MÉTODO PRINCIPAL - ATUALIZA PRODUTO COM HISTÓRICO EMBUTIDO
    # ──────────────────────────────────────────────
    def criar_upsert_produto(self, produto_doc):
        """
        Cria uma operação UpdateOne com upsert que:
        1. Atualiza dados atuais do produto
        2. Adiciona o preço ao histórico (se mudou)
        3. Atualiza min/max e contador
        """
        id_origem = produto_doc["id_origem"]
        mercado = produto_doc["mercado"]
        preco_novo = produto_doc["preco_atual"]
        data_coleta = produto_doc.get("data_ultima_coleta", datetime.now())
        data_str = data_coleta.strftime("%Y-%m-%d")
        
        return UpdateOne(
            {"id_origem": id_origem, "mercado": mercado},
            [
                {"$set": {
                    "preco_atual": preco_novo,
                    "data_ultima_coleta": data_coleta,
                    "nome": produto_doc["nome"],
                    "nome_normalizado": produto_doc["nome_normalizado"],
                    "ean": produto_doc["ean"],
                    "marca": produto_doc["marca"],
                    "categoria": produto_doc["categoria"],
                    "subcategoria": produto_doc["subcategoria"],
                    "preco_original": produto_doc["preco_original"],
                    "unidade": produto_doc["unidade"],
                    "url_imagem": produto_doc["url_imagem"],
                    "url_produto": produto_doc["url_produto"],
                    "is_kg": produto_doc["is_kg"],
                    "status": produto_doc["status"],
                }},
                {"$set": {
                    "historico_precos": {
                        "$cond": [
                            {"$or": [
                                {"$ne": ["$preco_atual", preco_novo]},
                                {"$eq": [{"$ifNull": ["$total_coletas", 0]}, 0]}
                            ]},
                            {"$concatArrays": [
                                {"$ifNull": ["$historico_precos", []]},
                                [{"data": data_str, "preco": preco_novo}]
                            ]},
                            {"$ifNull": ["$historico_precos", []]}
                        ]
                    }
                }},
                {"$set": {
                    "total_coletas": {
                        "$cond": [
                            {"$ne": ["$preco_atual", preco_novo]},
                            {"$add": [{"$ifNull": ["$total_coletas", 0]}, 1]},
                            {"$ifNull": ["$total_coletas", 0]}
                        ]
                    }
                }},
                {"$set": {
                    "menor_preco_historico": {
                        "$cond": [
                            {"$eq": [{"$ifNull": ["$menor_preco_historico", None]}, None]},
                            preco_novo,
                            {"$min": ["$menor_preco_historico", preco_novo]}
                        ]
                    }
                }},
                {"$set": {
                    "maior_preco_historico": {
                        "$cond": [
                            {"$eq": [{"$ifNull": ["$maior_preco_historico", None]}, None]},
                            preco_novo,
                            {"$max": ["$maior_preco_historico", preco_novo]}
                        ]
                    }
                }}
            ],
            upsert=True
        )
    
    # ──────────────────────────────────────────────
    # MÉTODOS DEPRECIADOS
    # ──────────────────────────────────────────────
    def salvar_historico(self, db, batch_h: list):
        """⚠️ DEPRECIADO: Histórico agora é embutido no produto."""
        if batch_h:
            print("⚠️ salvar_historico está DEPRECIADO. Histórico agora é embutido no produto.")
        pass

    def criar_historico(self, id_origem, preco, mercado, data=None):
        """⚠️ DEPRECIADO: Use apenas criar_upsert_produto()."""
        return {}

    # ──────────────────────────────────────────────
    # FECHAR CONEXÃO
    # ──────────────────────────────────────────────
    def fechar(self):
        """Fecha a conexão com MongoDB"""
        if self.client:
            self.client.close()