import re
import json
from playwright.sync_api import sync_playwright
from datetime import datetime
from scrapers.base_scraper import BaseScraper

class AtacadaoScraper(BaseScraper):
    def scrape(self, url):
        db = self.conectar()
        if db is None: return

        with sync_playwright() as p:
            # Mantemos visível para acompanhar a limpeza da tela
            browser = p.chromium.launch(headless=False) 
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            try:
                print(f"🌐 Acessando: {url}")
                page.goto(url, wait_until="networkidle", timeout=60000)

                # --- LIMPA-TRILHOS (BASEADO NO SEU HTML) ---
                print("🧹 Limpando obstáculos...")
                page.wait_for_timeout(2000)
                try:
                    # Seletor exato para o link que você mandou no HTML
                    btn_cookies = page.locator('a[role="button"]:has-text("Aceitar todos")')
                    if btn_cookies.is_visible():
                        btn_cookies.click()
                        print("✅ Botão de cookies clicado!")
                    
                    # Fecha o modal de localização (o cinza de Mogi Mirim)
                    page.keyboard.press("Escape")
                except:
                    pass

                # --- EXTRAÇÃO ---
                page.wait_for_selector('h1', timeout=15000)
                nome = page.locator('h1').inner_text().strip()
                
                # Captura todos os preços e pega o maior (unitário)
                print("💰 Extraindo valores...")
                elementos_preco = page.locator('span:has-text("R$"), div:has-text("R$")').all_inner_texts()
                
                valores = []
                for t in elementos_preco:
                    match = re.search(r'(\d+,\d+)', t)
                    if match:
                        v = float(match.group(1).replace(',', '.'))
                        if v > 1.0: # Filtra ruídos pequenos
                            valores.append(v)

                preco = max(valores) if valores else 0.0

                # ID de Origem (Extraindo os números finais da URL)
                id_match = re.search(r'-([\d-]+)/p', url)
                id_origem = id_match.group(1) if id_match else "N/A"

                produto = {
                    "id_origem": id_origem,
                    "nome": nome,
                    "preco": preco,
                    "mercado": "Atacadão",
                    "unidade": "Mogi Mirim",
                    "url_produto": url,
                    "data_extracao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "cru"
                }

                self.salvar_dados("precos_crus", [produto])
                print(f"🚀 SUCESSO: {nome} | R$ {preco} | ID: {id_origem}")

            except Exception as e:
                print(f"❌ Erro no Atacadão: {e}")
            finally:
                browser.close()

if __name__ == "__main__":
    url_teste = "https://www.atacadao.com.br/arroz-camil-agulhinha---tipo-1-pacote-com-5kg-12658-13743/p"
    scraper = AtacadaoScraper()
    scraper.scrape(url_teste)