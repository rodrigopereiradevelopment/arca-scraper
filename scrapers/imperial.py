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
                try:
                    page.wait_for_selector('button:has-text("ACEITAR E FECHAR")', timeout=4000)
                    page.click('button:has-text("ACEITAR E FECHAR")')
                    page.wait_for_timeout(1000)
                except:
                    pass
                page.wait_for_timeout(3000)
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                nome = "PRODUTO NAO IDENTIFICADO"
                # Seletor direto — classe exclusiva do nome do produto
                el_nome = soup.select_one('div.product-title-details')
                if el_nome:
                    nome = el_nome.text.strip().upper()
                    print(f"Nome via product-title-details: {nome}")
                # Fallback: último item do breadcrumb
                if nome == "PRODUTO NAO IDENTIFICADO":
                    items = soup.select('li.v-breadcrumbs-item')
                    if items:
                        ultimo = items[-1].text.strip().upper()
                        if ultimo and "HOME" not in ultimo:
                            nome = ultimo
                            print(f"Nome via breadcrumb: {nome}")
                preco = 0.0
                # Seletor direto do preço final
                el_preco = soup.select_one('div.product-preco-final-details span')
                if el_preco:
                    match = re.search(r'([\d]+[,\.][\d]+)', el_preco.text)
                    if match:
                        preco = float(match.group(1).replace('.', '').replace(',', '.'))
                        print(f"Preco via product-preco-final-details: R$ {preco}")
                # Fallback genérico
                if preco == 0.0:
                    for el in soup.find_all(string=re.compile(r'R\$\s*\d')):
                        texto = str(el).strip()
                        match = re.search(r'R\$\s*([\d]+[,\.][\d]+)', texto)
                        if match:
                            valor = float(match.group(1).replace('.', '').replace(',', '.'))
                            if valor > 0:
                                preco = valor
                                print(f"Preco via fallback: R$ {preco}")
                                break
                print(f"Imperial: {nome} | R$ {preco}")
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
                print(f"Erro ImperialScraper: {e}")
                return None
            finally:
                browser.close()
