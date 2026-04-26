"""
╔═══════════════════════════════════════════════════════════════════════════╗
║            PROJETO ARCA - Comparação de Preços                            ║
║                   Bot Acadêmico - São Vicente                             ║
╠═══════════════════════════════════════════════════════════════════════════╣
║ Este bot coleta preços para TCC na ETEC Pedro Ferreira Alves              ║
║ Objetivo: acessibilidade no consumo e ciência de dados                    ║
║ Não há intenção de sobrecarregar servidores.                              ║
║                                                                           ║
║ Desenvolvedor : Rodrigo                                                   ║
║ GitHub        : https://github.com/rodrigopereiradevelopment/arca-ionic   ║
║ Contato       : rodrigopereira.development@gmail.com                      ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import requests
import time
import unicodedata
import re
from datetime import datetime
from pymongo import UpdateOne
from scrapers.base_scraper import BaseScraper

def normalizar_nome(nome):
    if not nome: return "N/A"
    nome = unicodedata.normalize('NFKD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', nome).strip().upper()

class SaoVicenteScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.mercado = "São Vicente"
        self.unidade = "Mogi Mirim"
        self.base_url = "https://www.svicente.com.br/api/catalog_system/pub/products/search"
        
        self.headers = {
            "User-Agent": (
                "ARCA-Bot/1.0 (Bot Academico TCC ETEC; "
                "Contato: rodrigopereira.development@gmail.com; "
                "GitHub: https://github.com/rodrigopereiradevelopment/arca-ionic)"
            )
        }

        # Categorias completas que validamos hoje
        self.categorias = {
            "Mercearia": "1",
            "Bebidas": "10",
            "Bebidas Alcoolicas": "11",
            "Hortifruti": "2",
            "Carnes Aves Peixes": "3",
            "Frios Laticinios": "4",
            "Congelados": "5",
            "Higiene Beleza": "6",
            "Limpeza": "7",
            "Biscoitos Salgadinhos": "8",
            "Doces Sobremesas": "9",
            "Padaria": "12",
            "Saudaveis Organicos": "14",
            "Bazar Utilidades": "15",
            "Mundo Pet": "16"
        }

    def executar(self):
        db = self.conectar()
        if db is None: return

        print("🚀 São Vicente: Iniciando extração (QuickView JSON)...")

        for nome_cat, id_cat in self.categorias.items():
            print(f"\n📦 Categoria: {nome_cat}")
            
            offset = 0
            count = 50
            
            while True:
                # API REST do VTEX (São Vicente)
                url = f"{self.base_url}?fq=C:/{id_cat}/&_from={offset}&_to={offset + count - 1}"
                
                try:
                    res = requests.get(url, headers=self.headers, timeout=30)
                    
                    if res.status_code != 200:
                        break
                        
                    produtos_json = res.json()
                    if not produtos_json:
                        break

                    batch_p = []
                    batch_h = []

                    for prod in produtos_json:
                        try:
                            pid = prod.get('productId')
                            nome_raw = prod.get('productName')
                            
                            # Busca o preço no primeiro item da lista de skus
                            item = prod['items'][0]['sellers'][0]['commertialOffer']
                            preco = item.get('Price', 0)
                            preco_original = item.get('ListPrice', 0)

                            if preco <= 0: continue

                            img = prod['items'][0]['images'][0].get('imageUrl', "")
                            link = prod.get('link', "")

                            produto = {
                                "id_origem": pid,
                                "nome": nome_raw.upper(),
                                "nome_normalizado": normalizar_nome(nome_raw),
                                "categoria": nome_cat.upper(),
                                "preco": preco,
                                "preco_original": preco_original if preco_original > preco else None,
                                "mercado": self.mercado,
                                "unidade": self.unidade,
                                "url_imagem": img,
                                "url_produto": link,
                                "data_extracao": datetime.now(),
                                "status": "bronze"
                            }

                            batch_p.append(UpdateOne(
                                {"id_origem": pid, "mercado": self.mercado},
                                {"$set": produto},
                                upsert=True
                            ))

                            batch_h.append({
                                "id_origem": pid,
                                "preco": preco,
                                "mercado": self.mercado,
                                "data": datetime.now()
                            })

                        except (KeyError, IndexError):
                            continue

                    if batch_p:
                        db['produtos'].bulk_write(batch_p)
                        db['historico_precos'].insert_many(batch_h)
                        print(f"   ✅ Salvos: {len(batch_p)} produtos (offset {offset})")

                    if len(produtos_json) < count:
                        break

                    offset += count
                    time.sleep(0.15) # O "sweet spot" que você achou hoje!

                except Exception as e:
                    print(f"   ⚠️ Erro na conexão: {e}")
                    time.sleep(2) # Espera um pouco para tentar o próximo lote
                    offset += count
                    continue

        print("\n🏁 São Vicente: Concluído!")

if __name__ == "__main__":
    SaoVicenteScraper().executar()