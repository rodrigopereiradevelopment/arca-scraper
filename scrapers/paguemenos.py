"""
╔═══════════════════════════════════════════════════════════════════════════╗
║            PROJETO ARCA - Comparação de Preços                            ║
║                   Bot Acadêmico - Pague Menos                             ║
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

class PagueMenosScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.mercado = "PagueMenos"
        self.unidade = "Mogi Mirim"
        # Endpoint de busca da API do Pague Menos (VTEX)
        self.base_url = "https://www.superpaguemenos.com.br/api/catalog_system/pub/products/search"
        
        self.headers = {
            "User-Agent": (
                "ARCA-Bot/1.0 (Bot Academico TCC ETEC; "
                "Contato: rodrigopereira.development@gmail.com; "
                "GitHub: https://github.com/rodrigopereiradevelopment/arca-ionic)"
            )
        }

        # Categorias principais mapeadas
        self.categorias = {
            "Mercearia": "1",
            "Hortifruti": "2",
            "Carnes": "3",
            "Frios e Laticinios": "4",
            "Bebidas": "5",
            "Limpeza": "6",
            "Higiene e Beleza": "7",
            "Padaria": "8",
            "Congelados": "9",
            "Pet Shop": "10"
        }

    def executar(self):
        db = self.conectar()
        if db is None: return

        print(f"🚀 {self.mercado}: Iniciando extração total...")

        for nome_cat, id_cat in self.categorias.items():
            print(f"\n📦 Categoria: {nome_cat}")
            
            offset = 0
            count = 50 # Lote padrão para evitar timeout
            
            while True:
                # Paginação via fq (Filter Query) e range de produtos
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
                            
                            # Extração de preço e imagem do primeiro SKU disponível
                            sku = prod['items'][0]
                            offer = sku['sellers'][0]['commertialOffer']
                            
                            preco = offer.get('Price', 0)
                            preco_original = offer.get('ListPrice', 0)

                            if preco <= 0: continue

                            img = sku['images'][0].get('imageUrl', "")
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
                        print(f"   ✅ Processados: {len(batch_p)} itens (Offset {offset})")

                    if len(produtos_json) < count:
                        break

                    offset += count
                    time.sleep(0.2) # Delay de segurança para o Pague Menos

                except Exception as e:
                    print(f"   ⚠️ Erro: {e}")
                    time.sleep(5)
                    break

        print(f"\n🏁 {self.mercado}: Concluído com sucesso!")

if __name__ == "__main__":
    PagueMenosScraper().executar()