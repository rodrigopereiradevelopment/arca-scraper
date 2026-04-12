import re
from playwright.sync_api import sync_playwright
from datetime import datetime
from scrapers.base_scraper import BaseScraper

class SaoVicenteScraper(BaseScraper):
    def scrape(self, url):
        db = self.conectar()
        if db is None: return

        with sync_playwright() as p:
            # Lançamos o navegador com um 'slow_mo' para o site não se assustar
            browser = p.chromium.launch(headless=False, slow_mo=50)
            context = browser.new_context(
                viewport={'width': 1280, 'height': 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            try:
                print(f"🌐 Acessando São Vicente: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=60000)

                # --- COMPORTAMENTO HUMANO ---
                print("🖱️ Simulando atividade humana para liberar o preço...")
                page.wait_for_timeout(3000)
                page.mouse.wheel(0, 400) # Rola um pouco para baixo
                page.wait_for_timeout(1000)
                page.keyboard.press("Escape") # Fecha modais chatos
                page.wait_for_timeout(1000)

                # --- EXTRAÇÃO USANDO OS DADOS DO SEU F12 ---
                # Esperamos o elemento do preço aparecer fisicamente na tela
                print("🧐 Buscando elementos na página...")
                
                # Tenta capturar o nome
                nome = "N/A"
                try:
                    nome_selector = page.locator('.product-detail__title').first
                    nome_selector.wait_for(state="visible", timeout=10000)
                    nome = nome_selector.inner_text().strip()
                except:
                    nome = page.title().split('|')[0].strip()

                # Tenta capturar o preço
                preco = 0.0
                try:
                    # Buscamos a classe que você confirmou no F12
                    preco_selector = page.locator('.productPrice__price').first
                    preco_selector.wait_for(state="visible", timeout=10000)
                    texto_preco = preco_selector.inner_text()
                    
                    print(f"💰 Texto de preço capturado: {texto_preco}")
                    
                    # Extrai apenas os números e a vírgula
                    match = re.search(r'(\d+,\d+)', texto_preco)
                    if match:
                        preco = float(match.group(1).replace(',', '.'))
                except Exception as e:
                    print(f"⚠️ Não foi possível capturar o preço: {e}")

                # --- SALVAMENTO NO BANCO ---
                # Extrai o ID do final da URL (o 78166)
                id_origem = "N/A"
                id_match = re.search(r'-(\d+)\.html', url)
                if id_match:
                    id_origem = id_match.group(1)

                produto = {
                    "id_origem": id_origem,
                    "nome": nome,
                    "preco": preco,
                    "mercado": "São Vicente",
                    "unidade": "Mogi Mirim",
                    "url_produto": url,
                    "data_extracao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "cru"
                }

                self.salvar_dados("precos_crus", [produto])
                print(f"✅ SUCESSO NO ARCA: {nome} - R$ {preco}")

            except Exception as e:
                print(f"❌ Erro Crítico: {e}")
            finally:
                page.screenshot(path="debug_print.png")
                print("📸 Screenshot atualizado em debug_print.png")
                browser.close()

if __name__ == "__main__":
    # Usando a nova URL que você mandou
    url_teste = "https://www.svicente.com.br/arroz-tipo-1-camil-pacote-5kg-78166.html"
    scraper = SaoVicenteScraper()
    scraper.scrape(url_teste)