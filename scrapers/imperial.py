from scrapers.base_scraper import BaseScraper
import requests
from bs4 import BeautifulSoup
from datetime import datetime

class ImperialScraper(BaseScraper):
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

            # Extração baseada no seu print da escola
            nome = soup.find('div', class_='product-title-details').text.strip()
            
            # Pega o preço final e limpa a string (R$ 15,49 -> 15.49)
            preco_raw = soup.find('div', class_='product-price-final-details').find('span').text
            preco = float(preco_raw.replace('R$', '').replace(',', '.').strip())

            produto = {
                "id_origem": url.split('/')[-1], # Pega o EAN/Código no fim da URL
                "nome": nome,
                "preco": preco,
                "mercado": "Imperial",
                "unidade": "Mogi Mirim",
                "url_produto": url,
                "data_extracao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "cru"
            }

            self.salvar_dados("precos_crus", [produto])
            print(f"✅ IMPERIAL: {nome} - R$ {preco} capturado!")

        except Exception as e:
            print(f"❌ Erro ao raspar Imperial: {e}")

if __name__ == "__main__":
    url_teste = "https://onlinesim.com.br/supermercadoimperial/details/7896732400019"
    scraper = ImperialScraper()
    scraper.scrape(url_teste)