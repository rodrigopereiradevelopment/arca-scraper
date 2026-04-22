import requests
import time
import re
import unicodedata
from datetime import datetime
from pymongo import UpdateOne
from scrapers.base_scraper import BaseScraper

def normalizar_nome(nome):
    if not nome: return "N/A"
    nome = unicodedata.normalize('NFKD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', nome).strip().upper()

class PontoNovoScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.api     = "https://api.mobilesim.com.br"
        self.mercado = "Ponto Novo"
        self.unidade = "Mogi Mirim"

        self.headers = {
            "User-Agent":    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
            "Accept":        "application/json, text/plain, */*",
            "Origin":        "https://onlinesim.com.br",
            "Referer":       "https://onlinesim.com.br/",
            "Authorization": "Bearer owrF028ztCGzNh2nIr57mq447qKveGHr6bEGsgVPmjuxbiWPiZ5s2P0wEEjC9SXbZsh3r0JCXSvV4CRuRNrQQJ6mrav1C3mFfgyZ",
            "store":         "90",
            "isu":           "0",
            "platform":      "1",
            "version":       "v2.6.0"
        }

    def get(self, url):
        try:
            res = requests.get(url, headers=self.headers, timeout=15)
            if res.status_code == 200:
                return res.json()
            print(f"   ⚠️ {res.status_code} → {url}")
        except Exception as e:
            print(f"   ❌ {e}")
        return None

    def executar(self):
        db = self.conectar()
        if db is None:
            return

        print("🚀 Ponto Novo: Iniciando extração...")

        tabs_data = self.get(f"{self.api}/user/v1.02/tabs")
        if not tabs_data:
            print("❌ Falha ao buscar categorias. Verifique o token.")
            return

        categorias = [
            c for c in tabs_data.get("return", [])
            if "INSUMOS" not in c["name"].upper() and "CONSUMO" not in c["name"].upper()
        ]

        print(f"   📋 {len(categorias)} categorias encontradas")

        for cat in categorias:
            cat_id   = cat["id"]
            cat_nome = cat["name"]
            print(f"\n📦 {cat_nome} (ID: {cat_id})")

            subcat_data = self.get(f"{self.api}/user/v1.00/subcat/{cat_id}")
            ret = subcat_data.get("return") if subcat_data else None
            subcats = ret.get("subcategory", []) if ret else []

            if not subcats:
                subcats = [{"id_subcategoria": 0, "nome_subcategoria": cat_nome}]

            for sub in subcats:
                sub_id   = sub["id_subcategoria"]
                sub_nome = sub["nome_subcategoria"]

                pagina = 0
                while True:
                    feed_data = self.get(f"{self.api}/user/v1.03/feed/{sub_id}/{pagina}/{cat_id}")
                    if not feed_data:
                        break

                    ret = feed_data.get("return") or {}
                    produtos_raw = ret.get("products", [])
                    if not produtos_raw:
                        break

                    batch_p = []
                    batch_h = []

                    for p in produtos_raw:
                        try:
                            id_origem = str(p.get("sku", ""))
                            nome_raw  = p.get("name", "N/A")
                            preco     = float(p.get("price", 0.0))

                            if not id_origem or preco == 0:
                                continue

                            produto = {
                                "id_origem":        id_origem,
                                "ean":              p.get("barcode", "N/A"),
                                "nome":             nome_raw.upper(),
                                "nome_normalizado": normalizar_nome(nome_raw),
                                "categoria":        sub_nome.upper(),
                                "preco":            preco,
                                "mercado":          self.mercado,
                                "unidade":          self.unidade,
                                "url_imagem":       p.get("imghash", ""),
                                "data_extracao":    datetime.now(),
                                "status":           "bronze"
                            }

                            batch_p.append(UpdateOne(
                                {"id_origem": id_origem, "mercado": self.mercado},
                                {"$set": produto}, upsert=True
                            ))
                            batch_h.append({
                                "id_origem": id_origem,
                                "preco":     preco,
                                "mercado":   self.mercado,
                                "data":      datetime.now()
                            })
                        except Exception:
                            continue

                    if batch_p:
                        db['produtos'].bulk_write(batch_p)
                        db['historico_precos'].insert_many(batch_h)
                        print(f"   ✅ {len(batch_p)} produtos salvos ({sub_nome} p.{pagina})")

                    pagina += 1
                    time.sleep(0.5)

        print("\n🏁 Ponto Novo: Concluído!")

if __name__ == "__main__":
    PontoNovoScraper().executar()