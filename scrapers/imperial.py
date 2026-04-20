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

class ImperialScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.mobilesim.com.br/user/v1.02/feed/0/0/"
        self.headers = {
            "Authorization": "Bearer jrfX3qVkVBdiSrCLYyQzm3cQDB9WekXOczerypmC2jtpCUGGoRbiYXQnkvxcokutU90yNi7G2cQCA4CPld4HhhCcbj2f8WjJJrZE",
            "store": "147",
            "isu": "0",
            "platform": "1",
            "version": "v2.3.1",
            "origin": "https://onlinesim.com.br"
        }
        # IDs das abas (categorias) mapeadas - Adicione mais conforme precisar
        self.tabs = {
            "1": "ACOUGUE", 
            "23": "BEBIDAS", 
            "6": "CEREAIS", 
            "5": "BAZAR",
            "2": "HORTIFRUTI",
            "4": "LIMPEZA",     # Exemplo de nova categoria
            "14": "PADARIA"     # Exemplo de nova categoria
        }

    def testar_conexao(self):
        """Verifica se o token ainda é válido antes de começar"""
        try:
            res = requests.get(f"{self.base_url}1", headers=self.headers, timeout=5)
            return res.status_code == 200
        except:
            return False

    def executar(self):
        db_mongo = self.conectar()
        
        if db_mongo is None:
            print("❌ Falha na conexão com MongoDB")
            return
        
        print(f"🚀 Imperial: Iniciando extração via API (Bulk Mode)...")

        for tab_id, cat_nome in self.tabs.items():
            print(f"   Buscando categoria: {cat_nome}...")
            
            lista_produtos = []
            lista_historico = []

            try:
                res = requests.get(f"{self.base_url}{tab_id}", headers=self.headers, timeout=15)
                if res.status_code == 200:
                    produtos = res.json().get("return", {}).get("products", [])
                    
                    for p in produtos:
                        nome_raw = p.get("name", "").upper()
                        preco = float(p.get("price", 0))
                        
                        dados = {
                            "id_origem":        str(p.get("sku")),
                            "ean":              p.get("barcode") if len(str(p.get("barcode"))) >= 13 else "N/A",
                            "nome":             nome_raw,
                            "nome_normalizado": normalizar_nome(nome_raw),
                            "marca":            "N/A",
                            "categoria":        cat_nome,
                            "preco":            preco,
                            "mercado":          "Imperial",
                            "unidade":          "Mogi Mirim",
                            "url_imagem":       f"https://s3.amazonaws.com/images.mobilesim.com.br/{p.get('imghash')}.jpg" if p.get("imghash") else "N/A",
                            "data_extracao":    datetime.now(),
                            "status":           "bronze"
                        }

                        # Adiciona na fila de Update (Bulk)
                        lista_produtos.append(
                            UpdateOne(
                                {"id_origem": dados["id_origem"], "mercado": "Imperial"},
                                {"$set": dados},
                                upsert=True
                            )
                        )

                        # Adiciona na fila do Histórico
                        lista_historico.append({
                            "ean": dados["ean"],
                            "nome": dados["nome"],
                            "preco": dados["preco"],
                            "mercado": "Imperial",
                            "data": datetime.now()
                        })

                        # Salva de 50 em 50
                        if len(lista_produtos) >= 50:
                            db_mongo['produtos'].bulk_write(lista_produtos)
                            db_mongo['historico_precos'].insert_many(lista_historico)
                            lista_produtos = []
                            lista_historico = []

                    # Salva o que sobrou da categoria
                    if lista_produtos:
                        db_mongo['produtos'].bulk_write(lista_produtos)
                        db_mongo['historico_precos'].insert_many(lista_historico)

                    print(f"   ✅ {cat_nome}: {len(produtos)} produtos processados.")
                else:
                    print(f"   ⚠️ Erro na aba {cat_nome}: Status {res.status_code}")
                
                time.sleep(0.5) 
            except Exception as e:
                print(f"   ❌ Erro ao processar aba {cat_nome}: {e}")

        self.client.close()
        print("🏁 Imperial: Coleta finalizada!")

if __name__ == "__main__":
    scraper = ImperialScraper()
    scraper.executar()