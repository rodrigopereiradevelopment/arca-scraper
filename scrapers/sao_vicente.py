import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime
from scrapers.base_scraper import BaseScraper

class SaoVicenteScraper(BaseScraper):
    def scrape(self, url):
        db = self.conectar()
        if db is None: return

        # TUDO DAQUI PARA BAIXO PRECISA DE RECUO (TAB ou 4 ESPAÇOS)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True) 
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            )

            context.add_cookies([{
                'name': 'vtex_segment',
                'value': 'eyJjYW1wYWlnbiI6bnVsbCwiY2hhbm5lbCI6IjEiLCJwcmljZVRhYmxlIjpudWxsLCJyZWdpb24iOiJNM2R6Wld0MWJtUmhiR1Z1ZEdGeWFXOXVWVzVwWkdGMFpYTXVZMjltWlM1aWNRPT0ifQ==',
                'domain': '.svicente.com.br',
                'path': '/'
            }])

            page = context.new_page()

            try:
                print(f"🌐 Tentativa com Clique de Região: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=60000)

                # 1. TENTA CLICAR NO BOTÃO DE "CONFIRMAR" OU "LOJA" SE APARECER
                try:
                    # Espera um pouco para ver se a tela de "Bem-vindo" trava a página
                    page.wait_for_selector('button:has-text("Confirmar"), button:has-text("Entrar")', timeout=5000)
                    page.click('button:has-text("Confirmar"), button:has-text("Entrar")')
                    print("🖱️ Botão de boas-vindas clicado!")
                    page.wait_for_timeout(3000)
                except:
                    # Se não aparecer o botão, ele segue a vida
                    pass

                # 2. ROLAGEM PARA CARREGAR O PREÇO
                page.mouse.wheel(0, 800)
                page.wait_for_timeout(5000) 

                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # --- BUSCA PELO NOME REAL ---
                # No São Vicente, o nome real do produto costuma estar nessa classe:
                nome_tag = soup.select_one('h1.vtex-store-components-3-x-productNameContainer') or \
                           soup.select_one('.vtex-store-components-3-x-productBrand') or \
                           soup.find('h1')
                
                nome = nome_tag.text.strip() if nome_tag else "N/A"

                # Se ainda vier o "Bem-vindo", vamos forçar a extração do Título da página
                if "Bem-vindo" in nome:
                    # O título da página geralmente é: "Arroz Tipo 1 Camil... | São Vicente"
                    nome = soup.title.text.split('|')[0].strip() if soup.title else "N/A"

                # --- BUSCA PELO PREÇO ---
                preco = 0.0
                # O preço de venda na VTEX costuma ter essa classe:
                preco_tag = soup.select_one('.vtex-product-price-1-x-sellingPriceValue')
                
                if preco_tag:
                    texto_preco = re.sub(r'[^\d,]', '', preco_tag.text)
                    if texto_preco:
                        preco = float(texto_preco.replace(',', '.'))

                if nome == "N/A" or "Sites-SaoVicente" in nome:
                    meta_t = soup.find('meta', property='og:title')
                    if meta_t:
                        nome = meta_t['content'].split('|')[0].strip()

                id_sku = url.split('-')[-1].replace('/p', '')

                produto = {
                    "id_origem": id_sku,
                    "nome": nome,
                    "preco": preco,
                    "mercado": "São Vicente",
                    "unidade": "Mogi Mirim",
                    "url_produto": url,
                    "data_extracao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "cru"
                }

                self.salvar_dados("precos_crus", [produto])
                print(f"✅ SÃO VICENTE: {nome} - R$ {preco} capturado!")

            except Exception as e:
                print(f"❌ Erro: {e}")
            finally:
                browser.close()

# Adicione isso no final para o comando 'python -m scrapers.sao_vicente' funcionar
if __name__ == "__main__":
    url_teste = "https://www.svicente.com.br/arroz-tipo-1-agulhinha-camil-5kg/p"
    scraper = SaoVicenteScraper()
    scraper.scrape(url_teste)