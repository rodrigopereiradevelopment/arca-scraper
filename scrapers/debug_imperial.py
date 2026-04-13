# scrapers/imperial.py
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime

class ImperialScraper:
    def extrair(self, url_produto):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            try:
                page.goto(url_produto, wait_until="domcontentloaded", timeout=60000)

                # Espera qualquer elemento com preço ou nome carregar
                try:
                    page.wait_for_selector('h1, [class*="price"], [class*="produto"], [class*="product"]', timeout=10000)
                except:
                    print("⚠️ Timeout esperando elementos — tentando mesmo assim")

                page.mouse.wheel(0, 600)
                page.wait_for_timeout(3000)

                # Screenshot de diagnóstico (pode remover depois que funcionar)
                page.screenshot(path="debug_imperial.png")

                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # --- NOME ---
                nome = "PRODUTO NÃO IDENTIFICADO"
                for seletor in ['h1', 'h2', '[class*="name"]', '[class*="nome"]', '[class*="title"]']:
                    el = soup.select_one(seletor)
                    if el:
                        texto = el.text.strip().upper()
                        if texto and texto not in ["IMPERIAL", ""]:
                            nome = texto
                            break

                # Fallback: og:title
                if nome == "PRODUTO NÃO IDENTIFICADO":
                    meta = soup.find('meta', property='og:title')
                    if meta:
                        nome = meta.get('content', '').split('|')[0].strip().upper()

                # --- PREÇO ---
                preco = 0.0
                seletores_preco = [
                    '[class*="price"]',
                    '[class*="preco"]',
                    '[class*="valor"]',
                ]
                for seletor in seletores_preco:
                    el = soup.select_one(seletor)
                    if el:
                        match = re.search(r'\d+[,\.]\d+', el.text)
                        if match:
                            preco = float(match.group().replace('.', '').replace(',', '.'))
                            break

                # Fallback: qualquer R$ na página
                if preco == 0.0:
                    hint = soup.find(string=re.compile(r'R\$'))
                    if hint:
                        match = re.search(r'\d+[,\.]\d+', hint)
                        if match:
                            preco = float(match.group().replace('.', '').replace(',', '.'))

                print(f"🔍 Imperial — nome: {nome} | preço: {preco}")

                return {
                    "id_origem": url_produto.split('/')[-1],
                    "nome": nome,
                    "marca": "N/A",
                    "categoria": "Geral",
                    "preco": preco,
                    "mercado": "Imperial",
                    "unidade": "Mogi Mirim",
                    "url_imagem": "N/A",
                    "url_produto": url_produto,
                    "data_extracao": datetime.now().isoformat(),
                    "status": "raw"
                }

            except Exception as e:
                print(f"❌ Erro ImperialScraper: {e}")
                return None
            finally:
                browser.close()