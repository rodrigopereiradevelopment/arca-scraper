from scrapers.base_scraper import BaseScraper
import requests
from bs4 import BeautifulSoup
from datetime import datetime

class SaoVicenteScraper(BaseScraper):
    def scrape(self, url):
        db = self.conectar()
        if not db: return

        headers = {
            'User-Agent': 'ARCA-TCC-Project (contato: rodrigopereira.development@gmail.com)'
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')

            # 1. Nome: Está dentro de um <h3> com a classe 'product-detail__title'
            nome = soup.find('h3', class_='product-detail__title').text.strip()
            
            # 2. Preço: O valor de R$ 16,99 está em um <span> com classe 'productPrice'
            preco_tag = soup.find('span', class_='productPrice', attrs={'data-v-169ba803': True})
            # Se a busca por classe falhar, buscamos o texto que contém "R$"
            preco_raw = preco_tag.text if preco_tag else soup.find(string=lambda t: 'R$' in t)
            
            preco = float(preco_raw.replace('R$', '').replace(',', '.').strip())

            # 3. Marca: Está dentro do <p> com classe 'product-detail__brand'
            marca = soup.find('p', class_='product-detail__brand').find('span').text.strip()

            produto = {
                "id_origem": url.split('-')[-1].split('.')[0], # Pega o ID 915491 da URL
                "nome": nome,
                "marca": marca,
                "preco": preco,
                "mercado": "São Vicente",
                "unidade": "Mogi Mirim",
                "url_produto": url,
                "data_extracao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "cru"
            }

            self.salvar_dados("precos_crus", [produto])
            print(f"✅ SÃO VICENTE: {nome} - R$ {preco} salvo!")

        except Exception as e:
            print(f"❌ Erro São Vicente: {e}")

if __name__ == "__main__":
    url_teste = "https://www.svicente.com.br/arroz-tipo-1-são-pedro-agulhinha-pacote-5kg-915491.html"
    scraper = SaoVicenteScraper()
    scraper.scrape(url_teste)