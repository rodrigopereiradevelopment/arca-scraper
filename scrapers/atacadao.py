import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime
from scrapers.base_scraper import BaseScraper

class AtacadaoScraper(BaseScraper):
    def scrape(self, url):
        db = self.conectar()
        if db is None: return

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            page.route("**/*.{png,jpg,jpeg,svg,gif,woff,woff2}", lambda route: route.abort())
            page.route("**/google-analytics.com/**", lambda route: route.abort())

            try:
                print(f"🌐 Acessando Atacadão: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=60000)

                # Espera o nome do produto carregar
                page.wait_for_selector('h1[data-test="product-details-title"]', timeout=15000)
                page.wait_for_selector('p.text-2xl', timeout=10000)
                page.wait_for_timeout(500)

                # --- PREÇO via Playwright direto (mais confiável) ---
                preco = 0.0
                try:
                    preco_text = page.locator('p.text-2xl').first.inner_text()
                    match = re.search(r'([\d]+[,\.][\d]+)', preco_text)
                    if match:
                        preco = float(match.group(1).replace(',', '.'))
                except:
                    pass

                # Fallback via BeautifulSoup
                if preco == 0.0:
                    html = page.content()
                    soup = BeautifulSoup(html, 'html.parser')
                    preco_el = soup.select_one('p.text-2xl')
                    if preco_el:
                        match = re.search(r'([\d]+[,\.][\d]+)', preco_el.text)
                        if match:
                            preco = float(match.group(1).replace(',', '.'))

                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # --- NOME ---
                nome_el = soup.select_one('h1[data-test="product-details-title"]')
                nome = nome_el.text.strip().upper() if nome_el else "N/A"

                
                # --- CATEGORIA (breadcrumb) ---
                categoria = "GERAL"
                breadcrumbs = soup.select('nav[data-testid="breadcrumb"] a')
                if len(breadcrumbs) >= 2:
                    categoria = breadcrumbs[1].text.strip().upper()

                # --- ID DE ORIGEM ---
                id_match = re.search(r'-([\d]+-[\d]+)/p', url)
                id_origem = id_match.group(1) if id_match else "N/A"

                produto = {
                    "id_origem": id_origem,
                    "nome": nome,
                    "marca": "N/A",
                    "categoria": categoria,
                    "preco": preco,
                    "mercado": "Atacadão",
                    "unidade": "Mogi Mirim",
                    "url_produto": url,
                    "data_extracao": datetime.now().isoformat(),
                    "status": "raw"
                }

                self.salvar_dados("precos", [produto])
                print(f"✅ SUCESSO: {nome} | {categoria} | R$ {preco}")

            except Exception as e:
                print(f"❌ Erro no Atacadão: {e}")
            finally:
                browser.close()

if __name__ == "__main__":
    url_teste = "https://www.atacadao.com.br/arroz-camil-agulhinha---tipo-1-pacote-com-5kg-12658-13743/p"
    scraper = AtacadaoScraper()
    scraper.scrape(url_teste)