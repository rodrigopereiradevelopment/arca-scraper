import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from scrapers.base_scraper import BaseScraper

class AtacadaoScraper(BaseScraper):
    def scrape(self, url):
        db = self.conectar()
        if not db:
            return

        headers = {
            'User-Agent': 'ARCA-TCC-Project (contato: rodrigopereira.development@gmail.com)'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Tentar extrair do JSON interno (__NEXT_DATA__)
            script_tag = soup.find('script', id='__NEXT_DATA__')
            
            if script_tag:
                data = json.loads(script_tag.string)
                # O Atacadão costuma colocar os dados aqui:
                p_data = data['props']['pageProps']['product']
                nome = p_data.get('name')
                preco = p_data.get('price')
                id_sku = p_data.get('sku')
            else:
                # Scraping manual se o JSON falhar
                nome = soup.find('h1').text.strip()
                preco_raw = soup.find(string=lambda t: 'R$' in t).parent.text
                preco = float(preco_raw.replace('R$', '').replace('.', '').replace(',', '.').strip())
                id_sku = url.split('-')[-1].replace('/p', '')

            produto = {
                "id_origem": id_sku,
                "nome": nome,
                "preco": preco,
                "mercado": "Atacadão",
                "unidade": "Mogi Mirim",
                "url_produto": url,
                "data_extracao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "cru"
            }

            self.salvar_dados("precos_crus", [produto])
            print(f"✅ ATACADÃO: {nome} - R$ {preco} capturado com sucesso!")

        except Exception as e:
            print(f"❌ Erro ao raspar Atacadão: {e}")

if __name__ == "__main__":
    url_teste = "https://www.atacadao.com.br/arroz-camil-agulhinha---tipo-1-pacote-com-5kg-12658-13743/p"
    scraper = AtacadaoScraper()
    scraper.scrape(url_teste)