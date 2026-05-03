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
    - Normalização de nomes (remove acentos, uppercase, espaços)
    - Schema padrão de produto
    - Salvamento de produtos e histórico
    """
    
    # ──────────────────────────────────────────────
    # SCHEMA PADRÃO — todo scraper deve seguir
    # ──────────────────────────────────────────────
    SCHEMA_PRODUTO = {
        "id_origem":        str,      # Obrigatório — ID único no mercado
        "ean":              str,      # "N/A" se não disponível
        "nome":             str,      # Nome original uppercase
        "nome_normalizado": str,      # Normalizado (função abaixo)
        "marca":            str,      # "N/A" se não disponível
        "categoria":        str,      # Categoria do produto
        "subcategoria":     str,      # "" se não disponível
        "preco":            float,    # Preço final de venda
        "preco_original":   float,    # None se não houver desconto
        "mercado":          str,      # Nome do mercado
        "unidade":          str,      # Cidade/loja
        "url_imagem":       str,      # URL da imagem
        "url_produto":      str,      # "" se não disponível
        "is_kg":            int,      # 0 = unidade, 1 = kg (produto pesado)
        "data_extracao":    datetime, # Data/hora da coleta
        "status":           str,      # "bronze" (cru), "silver" (limpo), "gold" (pronto)
    }
    
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
            return self.db
        except Exception as e:
            print(f"❌ Erro de conexão no BaseScraper: {e}")
            return None

    # ──────────────────────────────────────────────
    # NORMALIZADOR CENTRALIZADO (ANTES DUPLICADO)
    # ──────────────────────────────────────────────
    @staticmethod
    def normalizar_nome(nome):
        """
        Normaliza nome de produto para comparação entre mercados.
        
        Exemplos:
        - "Coca-Cola 2L"      → "COCA COLA 2L"
        - "Arroz ão José 5kg" → "ARROZ AO JOSE 5KG"
        - None / ""            → "N/A"
        
        Regras:
        1. Remove acentos (NFKD)
        2. Converte para UPPERCASE
        3. Remove espaços múltiplos
        4. Remove espaços no início/fim
        """
        if not nome:
            return "N/A"
        nome = unicodedata.normalize('NFKD', str(nome))
        nome = ''.join(c for c in nome if not unicodedata.combining(c))
        return re.sub(r'\s+', ' ', nome).strip().upper()

    # ──────────────────────────────────────────────
    # CRIAÇÃO DE DOCUMENTO PADRONIZADO
    # ──────────────────────────────────────────────
    @classmethod
    def criar_produto(cls, **kwargs):
        """
        Cria um documento de produto seguindo o SCHEMA padrão.
        Preenche campos ausentes com defaults.
        
        Uso:
            produto = BaseScraper.criar_produto(
                id_origem="123",
                nome="Arroz 5kg",
                preco=22.90,
                mercado="GoodBom",
                ...
            )
        """
        defaults = {
            "id_origem":        kwargs.get("id_origem", ""),
            "ean":              kwargs.get("ean", "N/A"),
            "nome":             str(kwargs.get("nome", "N/A")).upper(),
            "nome_normalizado": cls.normalizar_nome(kwargs.get("nome", "")),
            "marca":            kwargs.get("marca", "N/A"),
            "categoria":        kwargs.get("categoria", ""),
            "subcategoria":     kwargs.get("subcategoria", ""),
            "preco":            float(kwargs.get("preco", 0)),
            "preco_original":   kwargs.get("preco_original", None),
            "mercado":          kwargs.get("mercado", ""),
            "unidade":          kwargs.get("unidade", ""),
            "url_imagem":       kwargs.get("url_imagem", ""),
            "url_produto":      kwargs.get("url_produto", ""),
            "is_kg":            int(kwargs.get("is_kg", 0)),
            "data_extracao":    kwargs.get("data_extracao", datetime.now()),
            "status":           kwargs.get("status", "bronze"),
        }
        
        # Se nome_normalizado foi passado manualmente, respeita
        if "nome_normalizado" in kwargs:
            defaults["nome_normalizado"] = kwargs["nome_normalizado"]
            
        return defaults

    # ──────────────────────────────────────────────
    # SALVAMENTO NO MONGODB
    # ──────────────────────────────────────────────
    def salvar_dados(self, colecao, dados):
        """Salva uma lista de documentos em qualquer coleção"""
        if self.db is not None and dados:
            self.db[colecao].insert_many(dados)
            print(f"✅ {len(dados)} documentos salvos na coleção {colecao}!")

    def salvar_historico(self, db, batch_h: list):
        """
        Salva histórico de preços com upsert por dia.
        Evita duplicatas no mesmo dia para o mesmo produto+mercado.
        """
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
        
        if ops:
            db['historico_precos'].bulk_write(ops)

    # ──────────────────────────────────────────────
    # CRIAÇÃO DE BULK DE UPSERT (PRODUTOS)
    # ──────────────────────────────────────────────
    def criar_upsert_produto(self, produto_doc):
        """
        Cria uma operação UpdateOne com upsert para produto.
        Filtro: id_origem + mercado (chave única)
        """
        return UpdateOne(
            {
                "id_origem": produto_doc["id_origem"],
                "mercado":   produto_doc["mercado"]
            },
            {"$set": produto_doc},
            upsert=True
        )

    def criar_historico(self, id_origem, preco, mercado, data=None):
        """Cria documento de histórico de preço padronizado"""
        return {
            "id_origem": str(id_origem),
            "preco":     float(preco),
            "mercado":   str(mercado),
            "data":      data if data else datetime.now()
        }

    # ──────────────────────────────────────────────
    # FECHAR CONEXÃO
    # ──────────────────────────────────────────────
    def fechar(self):
        """Fecha a conexão com MongoDB"""
        if self.client:
            self.client.close()