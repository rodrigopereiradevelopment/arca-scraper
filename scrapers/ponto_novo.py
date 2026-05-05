"""
╔═══════════════════════════════════════════════════════════════════════════╗
║            PROJETO ARCA - Comparação de Preços                            ║
║                   Bot Acadêmico - Ponto Novo                              ║
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
import os
from datetime import datetime
from scrapers.base_scraper import BaseScraper
from dotenv import load_dotenv

load_dotenv()


class PontoNovoScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.api = "https://api.mobilesim.com.br"
        self.mercado = "Ponto Novo"
        self.unidade = "Mogi Mirim"
        token = os.getenv("API_AUTHORIZATION_TOKEN")

        self.headers = {
            "User-Agent": (
                "ARCA-Bot/1.0 (Bot Academico TCC ETEC; "
                "Contato: rodrigopereira.development@gmail.com; "
                "GitHub: https://github.com/rodrigopereiradevelopment/arca-ionic)"
            ),
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "store": "90",
            "isu": "0",
            "platform": "1",
            "version": "v2.6.0"
        }

    def get(self, url):
        """Requisição GET com headers padrão"""
        try:
            res = requests.get(url, headers=self.headers, timeout=15)
            if res.status_code == 200:
                return res.json()
            print(f"   ⚠️ Status {res.status_code} na URL: {url}")
        except Exception as e:
            print(f"   ❌ Erro de conexão: {e}")
        return None

    def executar(self):
        db = self.conectar()
        if db is None:
            print("❌ Falha ao conectar ao Banco de Dados.")
            return

        print(f"🚀 {self.mercado}: Iniciando extração profunda...")

        tabs_data = self.get(f"{self.api}/user/v1.02/tabs")
        if not tabs_data or not tabs_data.get("return"):
            print(f"❌ Erro na resposta inicial: {tabs_data}")
            return

        categorias = tabs_data["return"]
        total_geral = 0

        for cat in categorias:
            cat_id, cat_nome = cat["id"], cat["name"].strip().upper()
            print(f"\n📂 CATEGORIA: {cat_nome} (ID: {cat_id})")

            sub_ids = None
            for versao in ["v1.02", "v1.01", "v1.00"]:
                subcat_data = self.get(f"{self.api}/user/{versao}/subcat/{cat_id}")
                if (subcat_data 
                        and subcat_data.get("return") 
                        and subcat_data["return"].get("subcategory")):
                    sub_ids = [int(s["id_subcategoria"]) for s in subcat_data["return"]["subcategory"]]
                    print(f"   📂 Subs oficiais: {sub_ids}")
                    break

            if sub_ids is None:
                sub_ids = list(range(0, 50))
                print(f"   ⚠️ Fallback: Varredura range(0, 50)")

            total_categoria = 0
            skus_da_categoria = set()

            for sub_id in sub_ids:
                pagina = 0
                itens_novos_nesta_sub = 0

                while True:
                    feed_url = f"{self.api}/user/v1.03/feed/{sub_id}/{pagina}/{cat_id}"
                    feed_data = self.get(feed_url)

                    if not feed_data or not feed_data.get("return"):
                        break

                    produtos_raw = feed_data["return"].get("products", [])
                    if not produtos_raw:
                        break

                    batch_p = []

                    for p in produtos_raw:
                        id_origem = str(p.get("sku", ""))

                        if not id_origem or p.get("catid") != cat_id or id_origem in skus_da_categoria:
                            continue

                        try:
                            preco_base = float(p.get("price", 0))
                            oferta = p.get("offer") or {}
                            preco_oferta = float(oferta.get("offer_connect", preco_base))
                            preco_final = preco_oferta if 0 < preco_oferta <= preco_base else preco_base

                            if preco_final <= 0:
                                continue

                            nome_raw = p.get("name", "N/A")
                            img_hash = p.get("imghash", "")
                            url_img = f"https://s3.mobilesim.com.br/images/products/{img_hash}.jpg" if img_hash else ""

                            produto = BaseScraper.criar_produto(
                                id_origem=id_origem,
                                ean=str(p.get("barcode", "N/A")),
                                nome=nome_raw,
                                categoria=cat_nome,
                                subcategoria=str(sub_id),
                                preco=preco_final,
                                preco_original=preco_base if preco_final < preco_base else None,
                                mercado=self.mercado,
                                unidade=self.unidade,
                                url_imagem=url_img,
                                is_kg=int(p.get("is_kg", 0)),
                            )

                            batch_p.append(self.criar_upsert_produto(produto))
                            skus_da_categoria.add(id_origem)
                            itens_novos_nesta_sub += 1

                        except Exception:
                            continue

                    if batch_p:
                        db['produtos'].bulk_write(batch_p)
                        total_categoria += len(batch_p)

                    if len(produtos_raw) < 30:
                        break
                    pagina += 1
                    time.sleep(0.1)

                if itens_novos_nesta_sub > 0:
                    print(f"   ✅ SubID {sub_id}: +{itens_novos_nesta_sub} itens (Total cat: {total_categoria})")

            print(f"   📊 TOTAL {cat_nome}: {total_categoria} produtos.")
            total_geral += total_categoria

        self.fechar()
        print(f"\n🏁 Ponto Novo: Concluído! Total geral: {total_geral} produtos")


if __name__ == "__main__":
    scraper = PontoNovoScraper()
    print("\n--- 🛒 Iniciando Coleta: Ponto Novo ---")
    try:
        scraper.executar()
        print("✅ Processo finalizado com sucesso!")
    except Exception as e:
        print(f"❌ Erro durante a execução: {e}")