import requests
import time
import re
import urllib3
from datetime import datetime
from pymongo import UpdateOne
from scrapers.base_scraper import BaseScraper

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def normalizar_nome(nome):
    import unicodedata
    nome = unicodedata.normalize('NFKD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', nome).strip().upper()

class SaoVicenteScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.grid_url      = "https://www.svicente.com.br/on/demandware.store/Sites-SaoVicente-Site/pt_BR/Search-UpdateGrid"
        self.quickview_url = "https://www.svicente.com.br/on/demandware.store/Sites-SaoVicente-Site/pt_BR/Product-ShowQuickView"

        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/html, */*",
            "Referer": "https://www.svicente.com.br"
        }

        self.categorias = {
            "Hortifruti": "010",
            "Mercearia":  "012",
            "Carnes":     "005",
            "Limpeza":    "011",
            "Bebidas":    "002",
            "Padaria":    "015",
            "Frios":      "008"
        }

    def buscar_ids(self, cgid, start, sz=50):
        params = {"cgid": cgid, "start": str(start), "sz": str(sz), "srule": "Price Ascending"}
        try:
            res = requests.get(self.grid_url, headers=self.headers, params=params, timeout=20, verify=False)
            if res.status_code == 200:
                data  = res.json()
                ids   = [p["productID"] for p in data.get("productSearch", {}).get("productIds", [])]
                total = data.get("productSearch", {}).get("count", 0)
                return ids, total
        except Exception as e:
            print(f"   ❌ Erro ao buscar IDs: {e}")
        return [], 0

    def buscar_produto(self, pid, tentativas=3):
        for i in range(tentativas):
            try:
                res = requests.get(self.quickview_url, headers=self.headers,
                                   params={"pid": pid}, timeout=15, verify=False)
                if res.status_code == 200:
                    return res.json()
            except requests.exceptions.Timeout:
                print(f"      ⏱️ Timeout pid={pid} (tentativa {i+1}/{tentativas})")
                time.sleep(2 * (i + 1))  # 2s, 4s, 6s
            except Exception as e:
                print(f"      ⚠️ Erro pid={pid}: {e}")
                break
        return None

    def parsear_produto(self, data, nome_cat):
        try:
            p = data.get("product", {})

            nome_raw = p.get("productName", "")
            if not nome_raw:
                return None

            preco = p.get("price", {}).get("sales", {}).get("value", 0.0)
            if not preco:
                return None

            imagens = p.get("images", {}).get("large", [])
            url_img = imagens[0].get("absURL", "") if imagens else ""

            return {
                "id_origem":        p.get("id", "N/A"),
                "nome":             nome_raw.upper(),
                "nome_normalizado": normalizar_nome(nome_raw),
                "marca":            p.get("brand", "N/A"),
                "categoria":        nome_cat.upper(),
                "preco":            float(preco),
                "mercado":          "São Vicente",
                "unidade":          "Mogi Mirim",
                "url_imagem":       url_img,
                "data_extracao":    datetime.now(),
                "status":           "bronze"
            }
        except Exception:
            return None

    def executar(self):
        db_mongo = self.conectar()
        if db_mongo is None:
            return

        print("🚀 São Vicente: Iniciando extração (QuickView JSON)...")

        for nome_cat, cgid in self.categorias.items():
            print(f"\n📦 Categoria: {nome_cat}")

            start = 0
            total = 1

            while start < total:
                ids, total = self.buscar_ids(cgid, start)
                if not ids:
                    break

                print(f"   📋 {len(ids)} IDs | offset {start}/{total}")

                batch_p = []
                batch_h = []

                for pid in ids:
                    data_prod = self.buscar_produto(pid)
                    if not data_prod:
                        continue

                    produto = self.parsear_produto(data_prod, nome_cat)
                    if not produto:
                        continue

                    batch_p.append(UpdateOne(
                        {"id_origem": pid, "mercado": "São Vicente"},
                        {"$set": produto}, upsert=True
                    ))
                    batch_h.append({
                        "id_origem": pid,
                        "preco":     produto["preco"],
                        "mercado":   "São Vicente",
                        "data":      datetime.now()
                    })

                    time.sleep(0.15)  # Reduzido de 0.3

                if batch_p:
                    db_mongo['produtos'].bulk_write(batch_p)
                    db_mongo['historico_precos'].insert_many(batch_h)
                    print(f"   ✅ Salvos: {len(batch_p)} produtos")

                start += len(ids)
                time.sleep(1)

        print("\n🏁 São Vicente: Concluído!")

if __name__ == "__main__":
    SaoVicenteScraper().executar()