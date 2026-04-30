"""
╔═══════════════════════════════════════════════════════════════════════════╗
║           PROJETO ARCA - Comparação de Preços                             ║
║                    Bot Acadêmico                                          ║
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
import re
import unicodedata
import os
from datetime import datetime
from pymongo import UpdateOne
from scrapers.base_scraper import BaseScraper
from dotenv import load_dotenv

load_dotenv()

def normalizar_nome(nome):
    if not nome: return "N/A"
    nome = unicodedata.normalize('NFKD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', nome).strip().upper()

class ImperialScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.api     = "https://api.mobilesim.com.br"
        self.mercado = "Imperial"
        self.unidade = "Mogi Mirim"
        token = os.getenv("IMPERIAL_TOKEN")

        self.headers = {
            "User-Agent": (
                "ARCA-Bot/1.0 (Bot Academico TCC ETEC; "
                "Contato: rodrigopereira.development@gmail.com; "
                "GitHub: https://github.com/rodrigopereiradevelopment/arca-ionic)"
            ),
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "store": "147",
            "isu": "0",
            "platform": "1",
            "version": "v2.3.1",
            "origin": "https://onlinesim.com.br"
        }

    def get(self, url):
        try:
            res = requests.get(url, headers=self.headers, timeout=15)
            if res.status_code == 200:
                return res.json()
        except Exception as e:
            print(f"   ❌ Erro: {e}")
        return None

    def executar(self):
        db = self.conectar()
        if db is None: return

        print(f"🚀 {self.mercado}: Iniciando extração profunda...")

        tabs_data = self.get(f"{self.api}/user/v1.02/tabs")
        if not tabs_data or not tabs_data.get("return"): 
            print("❌ Não foi possível carregar as abas principais.")
            return

        # Filtra categorias que não são produtos de prateleira
        categorias = [
            c for c in tabs_data["return"]
            if not any(x in c["name"].upper() for x in ["INSUMOS", "CONSUMO", "OUTRAS DESPESAS"])
        ]

        total_geral = 0

        for cat in categorias:
            cat_id, cat_nome = cat["id"], cat["name"]
            print(f"\n📂 CATEGORIA: {cat_nome.upper()} (ID: {cat_id})")

            # 1. Tenta obter subcategorias oficiais
            sub_ids = []
            subcat_data = self.get(f"{self.api}/user/v1.00/subcat/{cat_id}")
            if subcat_data and subcat_data.get("return"):
                ret = subcat_data["return"]
                if isinstance(ret, dict) and "subcategory" in ret:
                    sub_ids = [int(s["id_subcategoria"]) for s in ret["subcategory"]]
            
            if not sub_ids:
                print(f"   ⚠️ Varredura ativa (Range 0-60)...")
                sub_ids = sorted(list(set([0, cat_id] + list(range(1, 61)))))
            else:
                print(f"   📂 Subs oficiais: {sub_ids}")

            total_categoria = 0
            skus_da_categoria = set() # Evita duplicatas na mesma categoria

            for sub_id in sub_ids:
                pagina = 0
                itens_novos_nesta_sub = 0
                
                while True:
                    feed_url = f"{self.api}/user/v1.03/feed/{sub_id}/{pagina}/{cat_id}"
                    feed_data = self.get(feed_url)
                    
                    if not feed_data or not feed_data.get("return"): break

                    produtos_raw = feed_data["return"].get("products", [])
                    if not produtos_raw: break

                    batch_p, batch_h = [], []

                    for p in produtos_raw:
                        id_origem = str(p.get("sku", ""))
                        
                        # Filtros de segurança e integridade
                        if not id_origem or p.get("catid") != cat_id or id_origem in skus_da_categoria:
                            continue

                        try:
                            preco_base  = float(p.get("price", 0))
                            oferta      = p.get("offer") or {}
                            preco_clube = float(oferta.get("offer_connect", preco_base))
                            preco_final = preco_clube if 0 < preco_clube <= preco_base else preco_base

                            if preco_final <= 0: continue

                            nome_raw = p.get("name", "N/A")
                            img_hash = p.get("imghash", "")
                            url_img  = f"https://s3.mobilesim.com.br/images/products/{img_hash}.jpg" if img_hash else ""

                            produto_doc = {
                                "id_origem":        id_origem,
                                "ean":              str(p.get("barcode", "N/A")),
                                "nome":             nome_raw.upper(),
                                "nome_normalizado": normalizar_nome(nome_raw),
                                "categoria":        cat_nome.upper(),
                                "subcategoria_id":  sub_id,
                                "preco":            preco_final,
                                "preco_antigo":     preco_base if preco_final < preco_base else None,
                                "mercado":          self.mercado,
                                "unidade":          self.unidade,
                                "url_imagem":       url_img,
                                "data_extracao":    datetime.now(),
                                "status":           "bronze"
                            }

                            batch_p.append(UpdateOne(
                                {"id_origem": id_origem, "mercado": self.mercado},
                                {"$set": produto_doc}, upsert=True
                            ))
                            batch_h.append({
                                "id_origem": id_origem,
                                "preco":     preco_final,
                                "mercado":   self.mercado,
                                "data":      datetime.now()
                            })
                            skus_da_categoria.add(id_origem)
                            itens_novos_nesta_sub += 1

                        except Exception:
                            continue

                    if batch_p:
                        db['produtos'].bulk_write(batch_p)
                        db['historico_precos'].insert_many(batch_h)
                        total_categoria += len(batch_p)

                    if len(produtos_raw) < 30: break
                    pagina += 1
                    time.sleep(0.1)

                if itens_novos_nesta_sub > 0:
                    print(f"   ✅ SubID {sub_id:02}: +{itens_novos_nesta_sub} itens (Total cat: {total_categoria})")

            print(f"   📊 TOTAL {cat_nome}: {total_categoria} produtos.")
            total_geral += total_categoria

        self.client.close() 
        print(f"\n🏁 Imperial: Concluído! Total geral: {total_geral} produtos")
        
        
if __name__ == "__main__":
    scraper = ImperialScraper()
    print("\n--- 🛒 Iniciando Coleta: Imperial ---")
    try:
        scraper.executar()
        print("✅ Processo finalizado com sucesso!")
    except Exception as e:
        print(f"❌ Erro durante a execução: {e}")


