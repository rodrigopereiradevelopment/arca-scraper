from scrapers.base_scraper import BaseScraper
import requests
from bs4 import BeautifulSoup
from datetime import datetime

class PagueMenosScraper(BaseScraper):
    def scrape(self, url):
        db = self.conectar()
        if not db: return

        headers = {
            'User-Agent': 'ARCA-TCC-Project (contato: rodrigopereira.development@gmail.com)'
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')

            # 1. Nome: Usando o atributo itemprop="name" que aparece no seu print
            nome = soup.find('h1', attrs={'itemprop': 'name'}).text.strip()
            
            # 2. Preço: O Pague Menos usa <meta itemprop="price">. 
            # Isso é ótimo porque o valor já vem limpo (ex: 14.99)
            preco_tag = soup.find('meta', attrs={'itemprop': 'price'})
            preco = float(preco_tag['content']) if preco_tag else 0.0

            # 3. Marca: Também tem seu próprio itemprop
            marca_tag = soup.find('meta', attrs={'itemprop': 'brand'})
            marca = marca_tag['content'] if marca_tag else "N/A"

            # 4. ID (SKU): Fundamental para o seu banco
            sku_tag = soup.find('meta', attrs={'itemprop': 'sku'})
            sku = sku_tag['content'] if sku_tag else url.split('-')[-1].replace('/p', '')

            produto = {
                "id_origem": sku,
                "nome": nome,
                "marca": marca,
                "preco": preco,
                "mercado": "Pague Menos",
                "unidade": "Mogi Mirim",
                "url_produto": url,
                "data_extracao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "cru"
            }

            self.salvar_dados("precos_crus", [produto])
            print(f"✅ PAGUE MENOS: {nome} - R$ {preco} (OFERTA!)")

        except Exception as e:
            print(f"❌ Erro Pague Menos: {e}")

if __name__ == "__main__":
    url_teste = "https://www.superpaguemenos.com.br/arroz-raroz-tipo-1-5kg/p"
    scraper = PagueMenosScraper()
    scraper.scrape(url_teste)