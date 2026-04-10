import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from scrapers.base_scraper import BaseScraper

class AtacadaoScraper(BaseScraper):
    def scrape(self, url):
        db = self.conectar()
        if db is None: return

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')

            nome, preco, id_sku = "N/A", 0.0, "N/A"
            p_info = {} 

            # ESTRATÉGIA 1: Tentar extrair do script de dados do Next.js
            next_data = soup.find('script', id='__NEXT_DATA__')
            if next_data:
                try:
                    dados = json.loads(next_data.string)
                    props = dados.get('props', {}).get('pageProps', {})
                    p_info = props.get('product') or props.get('initialState', {}).get('product', {})
                    
                    if p_info:
                        nome = p_info.get('productName', nome)
                        id_sku = p_info.get('productReference', id_sku)
                        items = p_info.get('items', [])
                        if items:
                            sellers = items[0].get('sellers', [])
                            if sellers:
                                comm_data = sellers[0].get('commertialOffer', {})
                                preco = comm_data.get('Price') or comm_data.get('ListPrice') or 0.0
                except Exception as json_err:
                    print(f"⚠️ Erro ao processar JSON interno: {json_err}")

            # ESTRATÉGIA 2: Plano B (Meta Tags) - Se o JSON falhar ou vier N/A
            if preco == 0.0 or nome == "N/A":
                # Busca o Nome
                meta_nome = soup.find('meta', property='og:title') or \
                            soup.find('meta', name='twitter:title')
                if meta_nome:
                    nome = meta_nome.get('content', nome).split('|')[0].strip()

                # Busca o Preço
                if preco == 0.0:
                    preco_tag = soup.find('meta', property='product:price:amount')
                    if preco_tag:
                        try:
                            preco = float(preco_tag['content'])
                        except:
                            pass

            # Montagem do objeto para o MongoDB
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
            print(f"❌ Erro geral no Atacadão: {e}")

if __name__ == "__main__":
    url_teste = "https://www.atacadao.com.br/arroz-camil-agulhinha---tipo-1-pacote-com-5kg-12658-13743/p"
    scraper = AtacadaoScraper()
    scraper.scrape(url_teste)