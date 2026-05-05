"""
╔═══════════════════════════════════════════════════════════════════════════╗
║           PROJETO ARCA - Comparação de Preços                             ║
║                    Bot Acadêmico - Atacadão                               ║
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
import ftfy
import urllib3
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from scrapers.base_scraper import BaseScraper

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class AtacadaoScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.url_graphql = "https://www.atacadao.com.br/api/graphql"
        self.url_tree = "https://www.atacadao.com.br/io/api/catalog_system/pub/category/tree/3"
        self.mercado = "Atacadão"
        self.unidade = "Mogi Mirim"

        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": (
                "ARCA-Bot/1.0 (Bot Academico TCC ETEC; "
                "Contato: rodrigopereira.development@gmail.com; "
                "GitHub: https://github.com/rodrigopereiradevelopment/arca-ionic)"
            )
        }
        self.region_id = "v2.C65CCB3E6E9AAC0F04F39F5DF14AB96F"
        self.channel = '{"salesChannel":"1","seller":"atacadaobr945","regionId":"' + self.region_id + '"}'
        
        self.max_workers = 3
        self.delay_pagina = 0.3

    # ────────────────────────────────────────
    # MÉTODOS AUXILIARES
    # ────────────────────────────────────────
    def obter_categorias_dinamicas(self):
        """Mapeia a árvore de categorias do Atacadão via API REST"""
        print("🔍 Mapeando árvore do Atacadão...")
        try:
            time.sleep(2)
            res = requests.get(
                self.url_tree,
                headers=self.headers,
                timeout=20,
                verify=False,
                allow_redirects=True
            )
            if res.status_code != 200:
                print(f"   ⚠️ Status {res.status_code} na árvore de categorias")
                return []

            tree = res.json()
            lista_final = []
            seen = set()

            for cat_pai in tree:
                c1_nome = cat_pai['name'].upper()
                c1_slug = cat_pai['url'].rstrip('/').split('/')[-1]

                if cat_pai.get('children'):
                    for sub in cat_pai['children']:
                        c2_slug = sub['url'].rstrip('/').split('/')[-1]
                        chave = (c1_slug, c2_slug)
                        if chave not in seen:
                            seen.add(chave)
                            lista_final.append({
                                "label": c1_nome,
                                "cat1": c1_slug,
                                "cat2": c2_slug,
                                "nome_sub": sub['name']
                            })
                else:
                    chave = (c1_slug, c1_slug)
                    if chave not in seen:
                        seen.add(chave)
                        lista_final.append({
                            "label": c1_nome,
                            "cat1": c1_slug,
                            "cat2": c1_slug,
                            "nome_sub": cat_pai['name']
                        })
            return lista_final
        except Exception as e:
            print(f"❌ Erro ao mapear: {e}")
            return []

    def buscar_pagina(self, cat1, cat2, after):
        """Busca produtos via GraphQL com paginação por cursor"""
        payload = {
            "operationName": "ProductsQuery",
            "variables": {
                "selectedFacets": [
                    {"key": "category-1", "value": cat1},
                    {"key": "category-2", "value": cat2},
                    {"key": "channel",    "value": self.channel}
                ],
                "first": 50,
                "after": str(after),
                "sort": "score_desc",
                "term": ""
            },
            "query": """
                query ProductsQuery($selectedFacets: [IStoreSelectedFacet!]!, $first: Int!, $after: String!, $sort: StoreSort!, $term: String!) {
                    search(first: $first, after: $after, sort: $sort, term: $term, selectedFacets: $selectedFacets) {
                        products {
                            pageInfo { totalCount }
                            edges {
                                node {
                                    id slug sku name gtin
                                    brand { name }
                                    image { url }
                                    offers { lowPrice offers { price } }
                                }
                            }
                        }
                    }
                }
            """
        }
        try:
            res = requests.post(self.url_graphql, headers=self.headers, json=payload, timeout=20)
            if res.status_code == 200:
                return res.json()
            return None
        except Exception as e:
            print(f"   ❌ Erro na requisição: {e}")
            return None

    # ────────────────────────────────────────
    # PROCESSAMENTO PARALELO
    # ────────────────────────────────────────
    def processar_subcategoria(self, item):
        """
        Processa UMA subcategoria inteira.
        Usado pelo ThreadPoolExecutor — cada thread pega uma subcategoria.
        """
        cat_label = f"{item['label']} > {item['nome_sub']}"
        
        # Cada thread abre sua própria conexão MongoDB
        db = self.conectar()
        if db is None:
            print(f"   ❌ {cat_label}: Falha na conexão MongoDB")
            return 0

        after = 0
        total_cat = None
        total_sub = 0

        while True:
            dados = self.buscar_pagina(item['cat1'], item['cat2'], after)

            if dados is None or not isinstance(dados, dict):
                print(f"   ⚠️ {cat_label}: Falha na resposta. Pulando...")
                break

            data_content = dados.get("data")
            if not data_content or not data_content.get("search"):
                break

            products_data = data_content["search"].get("products")
            if not products_data:
                break

            if total_cat is None:
                total_cat = products_data.get("pageInfo", {}).get("totalCount", 0)
                if total_cat == 0:
                    break
                print(f"📦 {cat_label} ({total_cat} itens)")

            edges = products_data.get("edges", [])
            if not edges:
                break

            ops_produtos = []  # ← REMOVI ops_historico
            # ops_historico = []  ← REMOVER esta linha

            for edge in edges:
                p = edge["node"]
                nome_raw = ftfy.fix_text(p.get("name", "N/A")).strip().upper()

                # Preço
                offers = p.get("offers", {})
                preco = float(offers.get("lowPrice") or 0)
                if preco == 0 and offers.get("offers"):
                    preco = float(offers["offers"][0].get("price") or 0)

                # EAN (GTIN)
                gtin = str(p.get("gtin", ""))
                ean = gtin if len(gtin) >= 12 else "N/A"

                # Imagem
                img_node = p.get("image")
                if isinstance(img_node, list) and len(img_node) > 0:
                    url_imagem = img_node[0].get("url", "N/A")
                elif isinstance(img_node, dict):
                    url_imagem = img_node.get("url", "N/A")
                else:
                    url_imagem = "N/A"

                produto = BaseScraper.criar_produto(
                    id_origem=p.get("id"),
                    ean=ean,
                    nome=nome_raw,
                    marca=ftfy.fix_text(p.get("brand", {}).get("name", "N/A")),
                    categoria=item['label'],
                    subcategoria=item['nome_sub'],
                    preco=preco,
                    preco_original=None,
                    mercado=self.mercado,
                    unidade=self.unidade,
                    url_imagem=url_imagem,
                    is_kg=0,
                )

                ops_produtos.append(self.criar_upsert_produto(produto))
                # ops_historico.append(self.criar_historico(p.get("id"), preco, self.mercado))  ← REMOVER

            if ops_produtos:
                db['produtos'].bulk_write(ops_produtos)
                # self.salvar_historico(db, ops_historico)  ← REMOVER
                total_sub += len(ops_produtos)

            after += len(edges)
            print(f"   🔄 {cat_label}: {after}/{total_cat}")

            if after >= total_cat:
                break
            time.sleep(self.delay_pagina)

        print(f"   ✅ {cat_label}: {total_sub} produtos salvos")
        return total_sub

    # ────────────────────────────────────────
    # EXECUÇÃO PRINCIPAL
    # ────────────────────────────────────────
    def executar(self):
        categorias_alvo = self.obter_categorias_dinamicas()
        
        if not categorias_alvo:
            print("❌ Nenhuma categoria encontrada. Abortando.")
            return

        print(f"✅ {len(categorias_alvo)} subcategorias para processar.")
        print(f"🚀 Atacadão: Iniciando extração paralela ({self.max_workers} subcategorias simultâneas)...")

        total_geral = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.processar_subcategoria, item): item for item in categorias_alvo}

            for future in as_completed(futures):
                item = futures[future]
                try:
                    total = future.result()
                    total_geral += total
                except Exception as e:
                    print(f"   ❌ Erro em {item['label']} > {item['nome_sub']}: {e}")

        self.fechar()
        print(f"\n🏁 Atacadão: Concluído! Total geral: {total_geral} produtos")


if __name__ == "__main__":
    scraper = AtacadaoScraper()
    print("\n--- 🛒 Iniciando Coleta: Atacadão ---")
    inicio = time.time()
    try:
        scraper.executar()
        duracao = int(time.time() - inicio)
        print(f"⏱️ Tempo total: {timedelta(seconds=duracao)}")
        print("✅ Processo finalizado com sucesso!")
    except Exception as e:
        print(f"❌ Erro durante a execução: {e}")