import sqlite3
import requests
import re
import time
from bs4 import BeautifulSoup
from datetime import datetime
from scrapers.base_scraper import BaseScraper
from pymongo import UpdateOne

def normalizar_nome(nome):
    import unicodedata
    nome = unicodedata.normalize('NFKD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', nome).strip().upper()

class PagueMenosScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def extrair(self, url_produto, categoria_original):
        try:
            response = requests.get(url_produto, headers=self.headers, timeout=15)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # --- EXTRAÇÃO DO NOME ---
            # Tentamos o H1 ou a meta tag (mais estável em páginas de produto único)
            nome_tag = soup.find('h1') or soup.find('title')
            nome_raw = nome_tag.get_text(strip=True) if nome_tag else "PRODUTO SEM NOME"

            # --- EXTRAÇÃO DO PREÇO (Lógica Sniper com Regex) ---
            # Pegamos o texto da página toda para não errar a tag
            texto_pagina = soup.get_text()
            valores = re.findall(r"R\$\s?\d+,\d{2}", texto_pagina)
            
            preco = 0.0
            if valores:
                # O último valor R$ encontrado geralmente é o "Preço Por"
                preco_str = valores[-1].replace('R$', '').replace('.', '').replace(',', '.').strip()
                preco = float(preco_str)

            # --- EXTRAÇÃO DA IMAGEM ---
            img_tag = soup.find('img', {'id': 'image-main'}) or soup.find('meta', property="og:image")
            url_img = img_tag.get('src') or img_tag.get('content') if img_tag else "N/A"

            return {
                "id_origem": url_produto.split('/')[-2], # Pega o slug da URL como ID
                "ean": "N/A",
                "nome": nome_raw.upper(),
                "nome_normalizado": normalizar_nome(nome_raw),
                "marca": "N/A",
                "categoria": categoria_original.upper(),
                "preco": preco,
                "mercado": "PagueMenos",
                "unidade": "Mogi Mirim",
                "url_imagem": url_img,
                "url_produto": url_produto,
                "data_extracao": datetime.now(),
                "status": "bronze"
            }
        except Exception as e:
            print(f"   ⚠️ Erro ao extrair {url_produto}: {e}")
            return None

def processar_paguemenos():
    scraper = PagueMenosScraper()
    db_mongo = scraper.conectar()
    if db_mongo is None: return

    try:
        # --- MUDANÇA: Lendo da tabela específica que você criou ---
        conn = sqlite3.connect('arca.db')
        cursor = conn.cursor()
        cursor.execute("SELECT url, cat FROM links_paguemenos")
        produtos_sqlite = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"❌ Erro SQLite: {e}"); return

    print(f"🚀 Pague Menos: Processando {len(produtos_sqlite)} itens (Bulk Mode)...")

    lista_bulk = []
    lista_historico = []
    contador = 0

    for url, categoria in produtos_sqlite:
        dados = scraper.extrair(url, categoria)
        
        if dados and dados["preco"] > 0:
            # Upsert na coleção principal
            lista_bulk.append(
                UpdateOne(
                    {"id_origem": dados["id_origem"], "mercado": "PagueMenos"},
                    {"$set": dados},
                    upsert=True
                )
            )

            # Insert no histórico de preços
            lista_historico.append({
                "nome": dados["nome"],
                "preco": dados["preco"],
                "mercado": "PagueMenos",
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

        # Delay para não ser bloqueado (Pague Menos é sensível)
        time.sleep(1.2)

    # Limpeza final
    if lista_bulk:
        try:
            db_mongo['produtos'].bulk_write(lista_bulk)
            db_mongo['historico_precos'].insert_many(lista_historico)
        except Exception as e:
            print(f"   ❌ Erro no Bulk Final: {e}")

    scraper.client.close()
    print(f"🏁 Pague Menos: Finalizado! Total: {contador} itens salvos no Atlas.")

if __name__ == "__main__":
    processar_paguemenos()