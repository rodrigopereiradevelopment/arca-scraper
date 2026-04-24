import requests
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

class GoodBomScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.mercado  = "GoodBom"
        self.unidade  = "Mogi Mirim"
        self.base_url = "https://goodbom.com.br/pt/goodbom-mogi-mirim-sp"

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "RSC": "1"
        }

        # Categorias mapeadas no F12
        self.categorias = [
            "hortifrutigranjeiro-1",
            "acougue-47",
            "mercearia-3",
            "frios-e-laticinios-9",
            "padaria-50",
            "pet-shop-14",
            "peixaria-82",
            "magazine-16",
            "promocoes-99999",
        ]

    def buscar_pagina(self, slug, pagina):
        url = f"{self.base_url}/{slug}?page={pagina}"
        try:
            res = requests.get(url, headers=self.headers, timeout=20)
            if res.status_code == 200:
                return res.text
            print(f"   ⚠️ {res.status_code} → {url}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
        return None

    def parsear(self, texto, slug):
        return re.findall(
            r'"EcommerceProduct","id":"(\d+)"[^}]*?"name":"([^"]+)"[^}]*?"slug":"([^"]*)"[^}]*?"image":"([^"]*)"[^}]*?"price":([\d.]+)[^}]*?"priceWithDiscount":([\d.]+)',
            texto
        )

    def executar(self):
        db = self.conectar()
        if db is None:
            return

        print("🚀 GoodBom: Iniciando extração...")

        for slug in self.categorias:
            cat_nome = slug.rsplit("-", 1)[0].upper().replace("-", " ")
            print(f"\n📦 Categoria: {cat_nome}")

            pagina = 1
            total_salvos = 0

            while True:
                texto = self.buscar_pagina(slug, pagina)
                if not texto:
                    break

                produtos_raw = self.parsear(texto, slug)

                if not produtos_raw:
                    break

                batch_p = []
                batch_h = []

                for pid, nome_raw, produto_slug, img, preco_str, desconto_str in produtos_raw:
                    try:
                        preco_base    = float(preco_str)
                        preco_desc    = float(desconto_str)
                        preco_final   = preco_desc if preco_desc > 0 else preco_base

                        if preco_final == 0:
                            continue

                        # Tenta decodificar caracteres escapados (ex: \u00e7 → ç)
                        try:
                            nome_limpo = nome_raw.encode().decode('unicode_escape')
                        except Exception:
                            nome_limpo = nome_raw

                        produto = {
                            "id_origem":        pid,
                            "nome":             nome_limpo.upper(),
                            "nome_normalizado": normalizar_nome(nome_limpo),
                            "categoria":        cat_nome,
                            "preco":            preco_final,
                            "preco_original":   preco_base if preco_desc > 0 else None,
                            "mercado":          self.mercado,
                            "unidade":          self.unidade,
                            "url_imagem":       img,
                            "url_produto":      f"https://goodbom.com.br/pt/goodbom-mogi-mirim-sp/{produto_slug}",
                            "data_extracao":    datetime.now(),
                            "status":           "bronze"
                        }

                        batch_p.append(UpdateOne(
                            {"id_origem": pid, "mercado": self.mercado},
                            {"$set": produto},
                            upsert=True
                        ))
                        batch_h.append({
                            "id_origem": pid,
                            "preco":     preco_final,
                            "mercado":   self.mercado,
                            "data":      datetime.now()
                        })
                    except Exception:
                        continue

                if batch_p:
                    db['produtos'].bulk_write(batch_p)
                    db['historico_precos'].insert_many(batch_h)
                    total_salvos += len(batch_p)
                    print(f"   ✅ Pág {pagina}: {len(batch_p)} produtos salvos")

                # Se veio menos de 30 é a última página
                if len(produtos_raw) < 30:
                    break

                pagina += 1
                time.sleep(1)

            print(f"   🏁 {cat_nome}: {total_salvos} produtos no total")

        print("\n🏁 GoodBom: Concluído!")

if __name__ == "__main__":
    GoodBomScraper().executar()