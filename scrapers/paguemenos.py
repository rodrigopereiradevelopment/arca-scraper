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
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
from scrapers.base_scraper import BaseScraper

BASE = "https://www.superpaguemenos.com.br"

CATEGORIAS = {
    "mercearia": 4112,
    "bebidas": 2015,
    "higiene-e-beleza": 3382,
    "limpeza": 1348,
    "bazar": 1292,
    "frios-e-laticinios": 1009,
    "cafe-da-manha": 1072,
    "congelados": 576,
    "mamae-e-bebe": 823,
    "petshop": 425,
    "acougue": 314,
    "hortifruti": 249,
    "festivos": 419,
}

HEADERS = {
    'User-Agent': 'ARCA-Bot/1.0 (Bot Academico TCC ETEC; Contato: rodrigopereira.development@gmail.com)',
    'Accept': 'text/html,application/xhtml+xml,*/*;q=0.9',
    'Accept-Language': 'pt-BR,pt;q=0.9',
}


def extrair_produtos_pagina(soup, cat):
    """
    Extrai produtos de uma página HTML do Pague Menos.
    Retorna lista de dicionários com dados brutos (não normalizados).
    """
    produtos = []
    forms = soup.find_all('form', class_='product-form')
    
    for form in forms:
        try:
            data = json.loads(form.get('data-json', '{}'))
            slug_input = form.find('input', {'name': 'slug'})
            slug = slug_input['value'] if slug_input else ''
            url = f"{BASE}/{slug}/p" if slug else ''

            img_tag = form.find_previous('img')
            url_img = img_tag.get('data-src') or img_tag.get('src') if img_tag else 'N/A'

            nome = data.get('item_name', 'SEM NOME')
            preco = float(data.get('price', 0))
            if preco <= 0:
                continue

            produtos.append({
                "id_origem": str(data.get('item_id', slug)),  # Prefere item_id numérico
                "ean": "N/A",
                "nome": nome,
                "marca": data.get('item_brand', 'N/A'),
                "categoria": data.get('item_category1', cat),
                "subcategoria": data.get('item_category2', ''),
                "preco": preco,
                "url_imagem": url_img,
                "url_produto": url,
            })
        except:
            continue
    
    return produtos


class PagueMenosScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.mercado = "PagueMenos"
        self.unidade = "Mogi Mirim"

    def executar(self):
        db = self.conectar()
        if db is None:
            print("❌ Falha na conexão com MongoDB")
            return

        total_geral = 0

        for cat, qtd in CATEGORIAS.items():
            paginas_estimadas = (qtd // 30) + 5
            print(f"\n📦 {cat} (~{qtd} produtos)")
            cat_total = 0
            ultima_sig = None
            bulk_produtos = []  # ← REMOVI bulk_historico
            # bulk_historico = []  ← REMOVER

            for p in range(1, paginas_estimadas + 1):
                url = f"{BASE}/{cat}/?p={p}"
                try:
                    res = requests.get(url, headers=HEADERS, timeout=20)
                    if res.status_code != 200:
                        break

                    soup = BeautifulSoup(res.content, 'html.parser')
                    forms = soup.find_all('form', class_='product-form')

                    if not forms:
                        break

                    sig = '|'.join(str(json.loads(f.get('data-json', '{}')).get('item_id', '')) for f in forms)
                    if sig == ultima_sig:
                        break
                    ultima_sig = sig

                    produtos_raw = extrair_produtos_pagina(soup, cat)

                    for item in produtos_raw:
                        produto = BaseScraper.criar_produto(
                            id_origem=item["id_origem"],
                            ean=item["ean"],
                            nome=item["nome"],
                            marca=item["marca"],
                            categoria=item["categoria"].upper(),
                            subcategoria=item["subcategoria"],
                            preco=item["preco"],
                            preco_original=None,  # Site não mostra desconto
                            mercado=self.mercado,
                            unidade=self.unidade,
                            url_imagem=item["url_imagem"],
                            url_produto=item["url_produto"],
                            is_kg=0,
                        )

                        bulk_produtos.append(self.criar_upsert_produto(produto))
                        # ← REMOVI bulk_historico.append

                    cat_total += len(produtos_raw)

                    if len(bulk_produtos) >= 50:
                        db['produtos'].bulk_write(bulk_produtos)
                        # ← REMOVI self.salvar_historico
                        print(f"   💾 {cat_total} produtos salvos...")
                        bulk_produtos = []
                        # bulk_historico = []  ← REMOVER

                    print(f"   pág {p}: {len(produtos_raw)} produtos")
                    time.sleep(0.6)

                except Exception as e:
                    print(f"   ❌ Erro: {e}")
                    break

            if bulk_produtos:
                db['produtos'].bulk_write(bulk_produtos)
                # ← REMOVI self.salvar_historico

            total_geral += cat_total
            print(f"   ✅ {cat_total} produtos em {cat}")

        self.fechar()
        print(f"\n🏁 Pague Menos: Concluído! Total geral: {total_geral} produtos")


if __name__ == "__main__":
    scraper = PagueMenosScraper()
    print("\n--- 🛒 Iniciando Coleta: Pague Menos ---")
    try:
        scraper.executar()
        print("✅ Processo finalizado com sucesso!")
    except Exception as e:
        print(f"❌ Erro durante a execução: {e}")