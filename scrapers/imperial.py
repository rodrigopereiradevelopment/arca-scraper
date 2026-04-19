import requests
import time
from datetime import datetime
from scrapers.base_scraper import BaseScraper

# Importamos sua função de normalização se ela estiver no goodbom_scraper.py
# Caso contrário, pode copiar a função normalizar_nome para cá.
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
        # IDs das abas (categorias) que mapeamos
        self.tabs = {
            "1": "ACOUGUE", 
            "23": "BEBIDAS", 
            "6": "CEREAIS", 
            "5": "BAZAR",
            "2": "HORTIFRUTI"
        }

    def executar(self):
        db_mongo = self.conectar()
        
        # Bloco do IF (Se a conexão falhar)
        if db_mongo is None:
            print("❌ Falha na conexão com MongoDB")
            return
        
        # Daqui para baixo é o que acontece se a conexão der CERTO
        # Note que o print abaixo está alinhado com o "if"
        print(f"🚀 Imperial: Iniciando extração via API...")

        for tab_id, cat_nome in self.tabs.items():
            # ... resto do código continua aqui ...
            print(f"Buscando categoria: {cat_nome}...")
            try:
                res = requests.get(f"{self.base_url}{tab_id}", headers=self.headers, timeout=15)
                if res.status_code == 200:
                    produtos = res.json().get("return", {}).get("products", [])
                    
                    for p in produtos:
                        nome_raw = p.get("name", "").upper()
                        
                        # Montamos o dicionário principal
                        dados = {
                            "id_origem":        str(p.get("sku")),
                            "ean":              p.get("barcode") if len(str(p.get("barcode"))) >= 13 else "N/A",
                            "nome":             nome_raw,
                            "nome_normalizado": normalizar_nome(nome_raw),
                            "marca":            "N/A",
                            "categoria":        cat_nome,
                            "preco":            float(p.get("price", 0)),
                            "mercado":          "Imperial",
                            "unidade":          "Mogi Mirim",
                            "url_imagem":       f"https://s3.amazonaws.com/images.mobilesim.com.br/{p.get('imghash')}.jpg" if p.get("imghash") else "N/A",
                            "data_extracao":    datetime.now(),
                            "status":           "bronze"
                        }

                        # 1. UPSERT: Tabela de produtos (para o App)
                        # Identificador único aqui é SKU + Mercado
                        db_mongo['produtos'].update_one(
                            {"id_origem": dados["id_origem"], "mercado": "Imperial"},
                            {"$set": dados},
                            upsert=True
                        )

                        # 2. INSERT: Tabela de estatísticas (Histórico)
                        db_mongo['historico_precos'].insert_one({
                            "ean": dados["ean"],
                            "nome": dados["nome"],
                            "preco": dados["preco"],
                            "mercado": "Imperial",
                            "data": datetime.now()
                        })

                    print(f"✅ {cat_nome}: {len(produtos)} produtos processados.")
                else:
                    print(f"⚠️ Erro na aba {cat_nome}: Status {res.status_code}")
                
                time.sleep(1) # Delay entre abas para evitar bloqueio
            except Exception as e:
                print(f"❌ Erro ao processar aba {cat_nome}: {e}")

        self.client.close()
        print("🏁 Imperial: Coleta e Histórico finalizados!")

if __name__ == "__main__":
    scraper = ImperialScraper()
    scraper.executar()