import sqlite3
import requests
import re
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
                return None

            texto = response.text

            # --- EXTRAÇÃO COM REGEX ---
            code_match = re.search(r'"code":"(.*?)"', texto)
            ean_gtin = re.search(r'"gtin":"(\d{13})"', texto)
            ean_raw = re.search(r'(789\d{10})', texto)
            nome_match = re.search(r'"product":{.*?"name":"(.*?)"', texto)
            marca_match = re.search(r'"brand":"(.*?)"', texto)
            img_match = re.search(r'"image":"(.*?)"', texto)
            cat_match = re.search(r'"category":"(.*?)"', texto)

            ean_final = "N/A"
            if ean_gtin: ean_final = ean_gtin.group(1)
            elif ean_raw: ean_final = ean_raw.group(1)

            m_desc = re.search(r'"priceWithDiscount":\s*([\d.]+)', texto)
            m_norm = re.search(r'"price":\s*([\d.]+)', texto)
            preco = 0.0
            if m_desc and float(m_desc.group(1)) > 0:
                preco = float(m_desc.group(1))
            elif m_norm:
                preco = float(m_norm.group(1))

            nome_raw = nome_match.group(1) if nome_match else "PRODUTO SEM NOME"
            try:
                nome_limpo = nome_raw.encode().decode('unicode_escape')
            except:
                nome_limpo = nome_raw

            return {
                "id_origem": code_match.group(1) if code_match else url_produto.split('/')[-1],
                "ean": ean_final,
                "nome": nome_limpo.upper(),
                "nome_normalizado": normalizar_nome(nome_limpo),
                "marca": marca_match.group(1).upper() if marca_match else "N/A",
                "categoria": cat_match.group(1).upper() if cat_match else "GERAL",
                "preco": preco,
                "mercado": "GoodBom",
                "unidade": "Mogi Mirim",
                "url_imagem": img_match.group(1) if img_match else "N/A",
                "url_produto": url_produto,
                "data_extracao": datetime.now(),
                "status": "bronze"
            }
        except Exception:
            return None

def processar_banco():
    scraper = GoodBomScraper()
    db_mongo = scraper.conectar()
    if db_mongo is None: return

    try:
        conn = sqlite3.connect('arca.db')
        cursor = conn.cursor()
        cursor.execute("SELECT url FROM links")
        produtos_sqlite = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"❌ Erro SQLite: {e}"); return

    print(f"🚀 GoodBom: Coletando {len(produtos_sqlite)} itens (Bulk Mode)...")

    lista_bulk = []
    lista_historico = []
    contador = 0

    for (url,) in produtos_sqlite:
        dados = scraper.extrair(url)
        if dados:
            # Prepara o Update para a tabela principal
            lista_bulk.append(
                UpdateOne(
                    {"id_origem": dados["id_origem"], "mercado": "GoodBom"},
                    {"$set": dados},
                    upsert=True
                )
            )

            # Prepara o Insert para o histórico
            lista_historico.append({
                "ean": dados["ean"],
                "nome": dados["nome"],
                "preco": dados["preco"],
                "mercado": "GoodBom",
                "data": datetime.now()
            })

            contador += 1

            # DISPARO DO BULK (De 50 em 50)
            if len(lista_bulk) >= 50:
                try:
                    db_mongo['produtos'].bulk_write(lista_bulk)
                    db_mongo['historico_precos'].insert_many(lista_historico)
                    print(f"   💾 Checkpoint: {contador} produtos processados...")
                    lista_bulk = []
                    lista_historico = []
                except Exception as e:
                    print(f"   ❌ Erro no Bulk: {e}")

        # Sleep menor, já que o GoodBom é mais lento pra responder
        time.sleep(0.8)

    # SALVA O RESTANTE (O que sobrou da divisão por 50)
    if lista_bulk:
        try:
            db_mongo['produtos'].bulk_write(lista_bulk)
            db_mongo['historico_precos'].insert_many(lista_historico)
        except Exception as e:
            print(f"   ❌ Erro no Bulk Final: {e}")

    scraper.client.close()
    print(f"🏁 GoodBom: Finalizado! Total: {contador} itens.")

if __name__ == "__main__":
    processar_banco()