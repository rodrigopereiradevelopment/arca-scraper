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
import re
import time
import unicodedata
import ftfy
import urllib3
from datetime import datetime
from scrapers.base_scraper import BaseScraper
from pymongo import UpdateOne

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def normalizar_nome(nome):
    nome = unicodedata.normalize('NFKD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', nome).strip().upper()

class AtacadaoScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.url_graphql = "https://www.atacadao.com.br/api/graphql"
        self.url_tree = "https://www.atacadao.com.br/api/catalog_system/pub/category/tree/3"
        
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": (
                "ARCA-Bot/1.0 (Bot Academico TCC ETEC; "
                "Contato: rodrigopereira.development@gmail.com; "
                "GitHub: https://github.com/rodrigopereiradevelopment/arca-ionic)"
            )
        }
        # ID da Região para Mogi Mirim
        self.region_id = "v2.C65CCB3E6E9AAC0F04F39F5DF14AB96F"
        self.channel = '{"salesChannel":"1","seller":"atacadaobr945","regionId":"' + self.region_id + '"}'
    
    def obter_categorias_dinamicas(self):
        print("🔍 Mapeando árvore do Atacadão (Foco em Profundidade 2 para compatibilidade)...")
        try:
            time.sleep(2)
            res = requests.get(self.url_tree, headers=self.headers, timeout=20)
            if res.status_code != 200: return []
            
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

    def executar(self):
        db_mongo = self.conectar()
        if db_mongo is None: return

        categorias_alvo = self.obter_categorias_dinamicas()
        print(f"✅ {len(categorias_alvo)} subcategorias para processar.")

        total_geral = 0
        data_extracao = datetime.now()

        for item in categorias_alvo:
            print(f"\n📦 {item['label']} > {item['nome_sub']}")
            after = 0
            total_cat = None
            
            while True:
                dados = self.buscar_pagina(item['cat1'], item['cat2'], after)
                
                # --- VERIFICAÇÃO BLINDADA ---
                if dados is None or not isinstance(dados, dict):
                    print(f"   ⚠️ Falha na resposta (None). Tentando próxima categoria...")
                    break
                    
                data_content = dados.get("data")
                if not data_content or not data_content.get("search"):
                    print(f"   ⚠️ Dados de busca não encontrados. Pulando...")
                    break

                products_data = data_content["search"].get("products")
                if not products_data:
                    break
                # --- FIM DA VERIFICAÇÃO BLINDADA ---
                
                if total_cat is None:
                    # Blindagem do totalCount
                    total_cat = products_data.get("pageInfo", {}).get("totalCount", 0)
                    if total_cat == 0:
                        print("   (Vazio)")
                        break
                    print(f"   Itens: {total_cat}")

                edges = products_data.get("edges", [])
                if not edges: break

                ops_produtos = []
                ops_historico = []

                for edge in edges:
                    p = edge["node"]
                    nome_raw = ftfy.fix_text(p.get("name", "N/A")).strip().upper()
                    
                    offers = p.get("offers", {})
                    preco = float(offers.get("lowPrice") or 0)
                    if preco == 0 and offers.get("offers"):
                        preco = float(offers["offers"][0].get("price") or 0)
                    
                    gtin = str(p.get("gtin", ""))
                    ean = gtin if len(gtin) >= 12 else "N/A"

                    produto = {
                        "id_origem": p.get("id"),
                        "ean": ean,
                        "nome": nome_raw,
                        "nome_normalizado": normalizar_nome(nome_raw),
                        "marca": ftfy.fix_text(p.get("brand", {}).get("name", "N/A")),
                        "categoria": item['label'],
                        "subcategoria": item['nome_sub'],
                        "preco": preco,
                        "mercado": "Atacadão",
                        "unidade": "Mogi Mirim",
                        "url_imagem": p.get("image", [{}])[0].get("url", "N/A") if p.get("image") else "N/A",
                        "data_extracao": data_extracao,
                        "status": "bronze"
                    }

                    ops_produtos.append(UpdateOne(
                        {"id_origem": produto["id_origem"], "mercado": "Atacadão"},
                        {"$set": produto}, upsert=True
                    ))
                    ops_historico.append({
                        "id_origem": produto["id_origem"],
                        "preco": preco,
                        "mercado": "Atacadão",
                        "data": data_extracao
                    })

                if ops_produtos:
                    db_mongo['produtos'].bulk_write(ops_produtos)
                    db_mongo['historico_precos'].insert_many(ops_historico)
                    total_geral += len(ops_produtos)

                after += len(edges)
                print(f"   🔄 {after}/{total_cat}")

                if after >= total_cat: break
                time.sleep(0.3)

        self.client.close() 
        print(f"\n🏁 Atacadão: Concluído! Total geral: {total_geral} produtos")
        
        
if __name__ == "__main__":
    scraper = AtacadaoScraper()
    print("\n--- 🛒 Iniciando Coleta: Atacadão ---")
    try:
        scraper.executar()
        print("✅ Processo finalizado com sucesso!")
    except Exception as e:
        print(f"❌ Erro durante a execução: {e}")


