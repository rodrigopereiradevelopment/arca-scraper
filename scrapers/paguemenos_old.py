import re
from playwright.sync_api import sync_playwright
from datetime import datetime
from scrapers.base_scraper import BaseScraper

class PagueMenosScraper(BaseScraper):
    def scrape(self, url):
        db = self.conectar()
        if db is None: return

        with sync_playwright() as p:
            # Headless=False para você ver se ele pede o CEP
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            try:
                print(f"🌐 Acessando Pague Menos: {url}")
                page.goto(url, wait_until="networkidle", timeout=60000)

                # --- TRATAMENTO DE CEP (VTEX) ---
                print("📍 Verificando se pede CEP...")
                page.wait_for_timeout(3000)
                
                # Se aparecer o campo de CEP, a gente preenche
                # (Ajuste os seletores se o modal de CEP aparecer na sua tela)
                try:
                    input_cep = page.locator('input[placeholder*="CEP"], #ship-postalCode').first
                    if input_cep.is_visible():
                        input_cep.fill("13800202")
                        page.keyboard.press("Enter")
                        print("✅ CEP 13800-202 inserido!")
                        page.wait_for_timeout(3000)
                except:
                    pass

                # --- EXTRAÇÃO (USANDO O SEU F12) ---
                print("💰 Extraindo dados...")
                
                # Nome do produto (usando o itemprop="name" que costuma ter na VTEX)
                nome = page.locator('h1').inner_text().strip()

                # Preço: Vamos direto no meta itemprop="price" que você achou!
                # Ele é o mais preciso de todos.
                preco_raw = page.locator('meta[itemprop="price"]').get_attribute('content')
                preco = float(preco_raw) if preco_raw else 0.0

                produto = {
                    "id_origem": url.split('/')[-2], # Pega o slug do produto
                    "nome": nome,
                    "preco": preco,
                    "mercado": "Pague Menos",
                    "unidade": "Mogi Mirim",
                    "url_produto": url,
                    "data_extracao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "cru"
                }

                self.salvar_dados("precos_crus", [produto])
                print(f"🚀 SUCESSO PAGUE MENOS: {nome} | R$ {preco}")

            except Exception as e:
                print(f"❌ Erro no Pague Menos: {e}")
                page.screenshot(path="erro_paguemenos.png")
            finally:
                browser.close()

if __name__ == "__main__":
    # Link que você mandou
    url_teste = "https://www.superpaguemenos.com.br/arroz-raroz-tipo-1-5kg/p"
    scraper = PagueMenosScraper()
    scraper.scrape(url_teste)