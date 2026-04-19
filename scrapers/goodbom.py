import sqlite3
import requests
import re
import time
from datetime import datetime
from scrapers.base_scraper import BaseScraper

class GoodBomScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Rsc": "1"
        }

    def extrair(self, url_produto):
        try:
            response = requests.get(url_produto, headers=self.headers, timeout=15)
            response.encoding = 'utf-8'

            if response.status_code != 200:
                print(f"⚠️ Erro HTTP {response.status_code} → {url_produto}")
                return None

            texto = response.text

            # --- EXTRAÇÃO COM REGEX (Protegendo contra None) ---
            code_match = re.search(r'"code":"(.*?)"', texto)
            model_match = re.search(r'"modelId":"(.*?)"', texto)
            ean_gtin = re.search(r'"gtin":"(\d{13})"', texto)
            ean_raw = re.search(r'(789\d{10})', texto)
            nome_match = re.search(r'"product":{.*?"name":"(.*?)"', texto)
            marca_match = re.search(r'"brand":"(.*?)"', texto)
            img_match = re.search(r'"image":"(.*?)"', texto)
            cat_match = re.search(r'"category":"(.*?)"', texto)

            # Lógica do EAN
            ean_final = "N/A"
            if ean_gtin: ean_final = ean_gtin.group(1)
            elif ean_raw: ean_final = ean_raw.group(1)

            # Preço (Garantindo que seja float)
            m_desc = re.search(r'"priceWithDiscount":\s*([\d.]+)', texto)
            m_norm = re.search(r'"price":\s*([\d.]+)', texto)
            preco = 0.0
            if m_desc and float(m_desc.group(1)) > 0:
                preco = float(m_desc.group(1))
            elif m_norm:
                preco = float(m_norm.group(1))

            # Tratamento de Nome com Fallback
            nome_raw = nome_match.group(1) if nome_match else "PRODUTO SEM NOME"
            try:
                nome_limpo = nome_raw.encode().decode('unicode_escape').upper()
            except:
                nome_limpo = nome_raw.upper()

            return {
                "code": code_match.group(1) if code_match else "N/A",
                "model_id": model_match.group(1) if model_match else "N/A",
                "ean": ean_final,
                "nome": nome_limpo,
                "marca": marca_match.group(1) if marca_match else "N/A",
                "categoria": cat_match.group(1).upper() if cat_match else "GERAL",
                "preco": preco,
                "mercado": "GoodBom",
                "unidade": "Mogi Mirim",
                "url_imagem": img_match.group(1) if img_match else "N/A",
                "url_produto": url_produto,
                "data_extracao": datetime.now(), # Guardamos como objeto Date
                "status": "bronze"
            }
        except Exception as e:
            print(f"❌ Erro na extração: {e}")
            return None

def processar_banco():
    scraper = GoodBomScraper()
    db_mongo = scraper.conectar()
    if db_mongo is None: return

    try:
        conn = sqlite3.connect('arca.db')
        cursor = conn.cursor()
        cursor.execute("SELECT url FROM links")
        produtos = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"❌ Erro SQLite: {e}"); return

    print(f"🚀 Coletando {len(produtos)} itens...")

    for (url,) in produtos:
        dados = scraper.extrair(url)
        if dados:
            try:
                # 1. UPSERT: Mantém a tabela de busca do App atualizada
                db_mongo['produtos'].update_one(
                    {"url_produto": dados["url_produto"]},
                    {"$set": dados},
                    upsert=True
                )

                # 2. HISTÓRICO: Insere um novo registro para estatísticas
                db_mongo['historico_precos'].insert_one({
                    "ean": dados["ean"],
                    "nome": dados["nome"],
                    "preco": dados["preco"],
                    "mercado": dados["mercado"],
                    "data": datetime.now() # Objeto Date para gráficos
                })

                print(f"✅ {dados['nome'][:30]} | R$ {dados['preco']:.2f}")
            except Exception as e:
                print(f"❌ Erro Mongo: {e}")
        
        time.sleep(1.2)

    scraper.client.close()
    print("🏁 Finalizado!")

if __name__ == "__main__":
    processar_banco()