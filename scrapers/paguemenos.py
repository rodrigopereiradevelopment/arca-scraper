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
import re
import time
import unicodedata
from datetime import datetime
from pymongo import UpdateOne
from scrapers.base_scraper import BaseScraper

def normalizar_nome(nome):
    if not nome: return "N/A"
    nome = unicodedata.normalize('NFKD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', nome).strip().upper()

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
                "id_origem": slug,
                "ean": "N/A",
                "nome": nome.upper(),
                "nome_normalizado": normalizar_nome(nome),
                "marca": data.get('item_brand', 'N/A').upper(),
                "categoria": data.get('item_category1', cat).upper(),
                "subcategoria": data.get('item_category2', ''),
                "preco": preco,
                "mercado": "PagueMenos",
                "unidade": "Mogi Mirim",
                "url_imagem": url_img,
                "url_produto": url,
                "data_extracao": datetime.now(),
                "status": "bronze"
            })
        except:
            continue
    return produtos

class PagueMenosScraper(BaseScraper):
    def __init__(self):
        super().__init__()

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
            bulk_produtos = []
            bulk_historico = []

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

                    produtos = extrair_produtos_pagina(soup, cat)

                    for prod in produtos:
                        bulk_produtos.append(
                            UpdateOne(
                                {"id_origem": prod["id_origem"], "mercado": "PagueMenos"},
                                {"$set": prod},
                                upsert=True
                            )
                        )
                        bulk_historico.append({
                            "nome": prod["nome"],
                            "preco": prod["preco"],
                            "mercado": "PagueMenos",
                            "data": datetime.now()
                        })

                    cat_total += len(produtos)

                    if len(bulk_produtos) >= 50:
                        db['produtos'].bulk_write(bulk_produtos)
                        db['historico_precos'].insert_many(bulk_historico)
                        print(f"   💾 {cat_total} produtos salvos...")
                        bulk_produtos = []
                        bulk_historico = []

                    print(f"   pág {p}: {len(produtos)} produtos")
                    time.sleep(0.6)

                except Exception as e:
                    print(f"   ❌ Erro: {e}")
                    break

            if bulk_produtos:
                db['produtos'].bulk_write(bulk_produtos)
                db['historico_precos'].insert_many(bulk_historico)

            total_geral += cat_total
            print(f"   ✅ {cat_total} produtos em {cat}")

        self.client.close()
        print(f"\n🏁 CONCLUÍDO! {total_geral} produtos salvos!")
