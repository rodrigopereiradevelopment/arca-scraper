import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from scrapers.base_scraper import BaseScraper

class SaoVicenteScraper(BaseScraper):
    def scrape(self, url):
        db = self.conectar()
        if db is None: return

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            nome, preco, id_sku = "N/A", 0.0, url.split('-')[-1].replace('/p', '')

            # ESTRATÉGIA: Procurar no Script JSON-LD (O favorito do Google)
            scripts = soup.find_all('script', type='application/ld+json')
            for s in scripts:
                try:
                    dados = json.loads(s.string)
                    # O JSON-LD pode ser um dicionário ou uma lista
                    if isinstance(dados, list): dados = dados[0]
                    
                    if 'name' in dados:
                        nome = dados['name']
                    
                    if 'offers' in dados:
                        offers = dados['offers']
                        # Às vezes o preço está em 'price' ou 'lowPrice'
                        p = offers.get('price') or offers.get('lowPrice')
                        if p: preco = float(str(p).replace(',', '.'))
                        break # Se achou o preço, para de procurar nos scripts
                except:
                    continue

            # FALLBACK: Se o JSON falhar, tenta pegar o Título da página
            if nome == "N/A":
                nome = soup.title.text.split('|')[0].strip() if soup.title else "N/A"

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
            print(f"✅ SÃO VICENTE: {nome} - R$ {preco} capturado com sucesso!")

        except Exception as e:
            print(f"❌ Erro São Vicente: {e}")

if __name__ == "__main__":
    url_teste = "https://www.svicente.com.br/arroz-tipo-1-agulhinha-camil-5kg/p"
    scraper = SaoVicenteScraper()
    scraper.scrape(url_teste)