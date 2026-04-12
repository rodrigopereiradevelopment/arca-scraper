import re
from playwright.sync_api import sync_playwright
from datetime import datetime
from scrapers.base_scraper import BaseScraper

class ImperialScraper(BaseScraper):
    def scrape(self, url):
        db = self.conectar()
        if db is None: return

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            try:
                print(f"🌐 Acessando Imperial: {url}")
                page.goto(url, wait_until="networkidle", timeout=60000)

                # --- LIMPA-TRILHOS ---
                print("🧹 Removendo obstáculos...")
                page.wait_for_timeout(3000)
                
                try:
                    btn_cookies = page.locator('button:has-text("ACEITAR E FECHAR")')
                    if btn_cookies.is_visible():
                        btn_cookies.click()
                        print("✅ Cookies aceitos!")
                except:
                    pass

                page.keyboard.press("Escape")
                page.wait_for_timeout(1000)

                # --- EXTRAÇÃO (AJUSTADA PELO SEU F12) ---
                print("💰 Localizando preço e nome...")
                
                # Espera a classe que você confirmou no F12
                page.wait_for_selector('.product-preco-final-details', timeout=15000)
                
             # 1. Nome do Produto (Com espera e seletores alternativos)
                try:
                    # Espera um pouco pelo título antes de desistir
                    page.wait_for_selector('h1, .product-title-details, .product-name', timeout=5000)
                    
                    # Tenta pegar o h1, se não der, tenta as classes comuns de e-commerce
                    nome_element = page.locator('h1, .product-title-details, .product-name').first
                    nome = nome_element.inner_text().strip()
                    
                    # Se por algum motivo o nome vier vazio, joga o fallback
                    if not nome:
                        nome = "Produto Imperial"
                except:
                    nome = "Produto Imperial"
                # 2. Preço
                texto_preco_raw = page.locator('.product-preco-final-details').inner_text()
                match = re.search(r'(\d+,\d+)', texto_preco_raw)
                preco = 0.0
                if match:
                    preco = float(match.group(1).replace(',', '.'))

                produto = {
                    "id_origem": url.split('/')[-1], 
                    "nome": nome,
                    "preco": preco,
                    "mercado": "Imperial",
                    "unidade": "Mogi Mirim",
                    "url_produto": url,
                    "data_extracao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "cru"
                }

                self.salvar_dados("precos_crus", [produto])
                print(f"🚀 SUCESSO IMPERIAL: {nome} | R$ {preco}")

            except Exception as e:
                print(f"❌ Erro no Imperial: {e}")
                page.screenshot(path="erro_imperial.png")
            finally:
                browser.close()

if __name__ == "__main__":
    url_teste = "https://onlinesim.com.br/supermercadoimperial/details/7896732400019"
    scraper = ImperialScraper()
    scraper.scrape(url_teste)