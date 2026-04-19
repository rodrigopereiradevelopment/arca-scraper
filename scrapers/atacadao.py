import requests
import time
from datetime import datetime
from scrapers.base_scraper import BaseScraper
from pymongo import UpdateOne

def normalizar_nome(nome):
    import unicodedata
    import re
    nome = unicodedata.normalize('NFKD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', nome).strip().upper()

class AtacadaoScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.url = "https://www.atacadao.com.br/api/graphql"
        
        # Headers atualizados: VTEX exige User-Agent real
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*"
        }
        
        # O SEGREDO: Usando o ID da região exato que você pegou no navegador
        # Note que removi o "v2." e usei o valor que você encontrou na URL
        self.region_id = "U1cjYXRhY2FkYW9icjk0NQ==" 
        self.channel = '{"salesChannel":"1","seller":"atacadaobr945","regionId":"' + self.region_id + '"}'

        self.categorias = {
            "Arroz":        ("mercearia", "graos",              "Arroz"),
            "Feijão":       ("mercearia", "graos",              "Feijão"),
            "Óleo":         ("mercearia", "azeites-oleos-e-vinagres", "Óleos"),
            "Café":         ("mercearia", "cafes-chas-e-achocolatados", "Café"),
            "Macarrão":     ("mercearia", "massas-e-molhos",    "Macarrão"),
            "Biscoitos":    ("mercearia", "biscoitos",          "Biscoitos"),
            "Açúcar":       ("mercearia", "acucar-e-adocantes", "Açúcar"),
            "Limpeza":      ("limpeza",   "limpeza-de-roupas",  "Limpeza"),
            "Higiene":      ("higiene-e-perfumaria", "higiene-bucal", "Higiene"),
            "Leite":        ("padaria-e-matinais", "leites",    "Leite"),
        }

    def buscar_pagina(self, cat1, cat2, after):
        # Montando a Query GraphQL corretamente
        payload = {
            "operationName": "ProductsQuery",
            "variables": {
                "selectedFacets": [
                    {"key": "category-1", "value": cat1},
                    {"key": "category-2", "value": cat2},
                    {"key": "region-id",  "value": self.region_id}, # Campo essencial
                    {"key": "channel",    "value": self.channel}
                ],
                "first": 50,
                "after": str(after),
                "sort":  "score_desc",
                "term":  ""
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
                                    offers {
                                        lowPrice highPrice
                                        offers { price listPrice minQuantity unitPerBox }
                                    }
                                    breadcrumbList {
                                        itemListElement { name position }
                                    }
                                }
                            }
                        }
                    }
                }
            """
        }

        try:
            # Atacadão prefere POST para queries complexas
            res = requests.post(self.url, headers=self.headers, json=payload, timeout=20)
            
            if res.status_code == 200:
                return res.json()
            else:
                print(f"   ⚠️ Status {res.status_code} na categoria {cat1}")
        except Exception as e:
            print(f"   ❌ Erro na requisição: {e}")
        return None

    def executar(self):
        db_mongo = self.conectar()
        
        if db_mongo is None:
            print("❌ Falha na conexão com MongoDB")
            return

        print("🚀 Atacadão: Iniciando extração via API (GraphQL)...")

        for nome_cat, (cat1, cat2, cat_label) in self.categorias.items():
            print(f"\n📦 Categoria: {nome_cat}")

            lista_produtos  = []
            lista_historico = []
            after = 0
            total_count = 0

            dados_json = self.buscar_pagina(cat1, cat2, after)
            if not dados_json or "data" not in dados_json:
                print(f"   ⚠️ Sem dados para {nome_cat}. Verifique os Headers/RegionID.")
                continue

            search = dados_json.get("data", {}).get("search", {})
            products_data = search.get("products", {})
            total_count = products_data.get("pageInfo", {}).get("totalCount", 0)
            
            print(f"   Encontrados: {total_count} produtos.")

            # Loop de paginação
            while after < total_count and after < 200:
                if after > 0: # Não busca a primeira página de novo
                    dados_json = self.buscar_pagina(cat1, cat2, after)
                
                if not dados_json: break
                
                edges = dados_json.get("data", {}).get("search", {}).get("products", {}).get("edges", [])
                if not edges: break

                for edge in edges:
                    p = edge.get("node", {})
                    nome_raw = p.get("name", "N/A").upper()
                    
                    # Preço no Atacadão às vezes vem dentro de 'offers'
                    offers_data = p.get("offers", {})
                    preco = offers_data.get("lowPrice", 0.0)
                    
                    # Se preço for 0, tenta pegar do primeiro item da lista de ofertas
                    if preco == 0 and offers_data.get("offers"):
                        preco = offers_data["offers"][0].get("price", 0.0)

                    imagem = p.get("image", [{}])[0].get("url", "N/A")
                    
                    produto = {
                        "id_origem":        p.get("id", "N/A"),
                        "ean":              p.get("gtin", "N/A"),
                        "nome":             nome_raw,
                        "nome_normalizado": normalizar_nome(nome_raw),
                        "marca":            p.get("brand", {}).get("name", "N/A"),
                        "categoria":        nome_cat.upper(),
                        "preco":            float(preco),
                        "mercado":          "Atacadão",
                        "unidade":          "Mogi Mirim",
                        "url_imagem":       imagem,
                        "data_extracao":    datetime.now(),
                        "status":           "bronze"
                    }

                    lista_produtos.append(
                        UpdateOne(
                            {"id_origem": produto["id_origem"], "mercado": "Atacadão"},
                            {"$set": produto},
                            upsert=True
                        )
                    )

                    lista_historico.append({
                        "id_origem": produto["id_origem"],
                        "preco":     produto["preco"],
                        "mercado":   "Atacadão",
                        "data":      datetime.now()
                    })

                after += len(edges)
                print(f"   🔄 Processados: {after}/{total_count}")
                time.sleep(1)

            # Salva no Banco
            if lista_produtos:
                try:
                    db_mongo['produtos'].bulk_write(lista_produtos)
                    db_mongo['historico_precos'].insert_many(lista_historico)
                    print(f"✅ {nome_cat} finalizado com sucesso!")
                except Exception as e:
                    print(f"❌ Erro ao salvar no Mongo: {e}")

        print("\n🏁 Atacadão: Coleta finalizada!")

if __name__ == "__main__":
    scraper = AtacadaoScraper()
    scraper.executar()