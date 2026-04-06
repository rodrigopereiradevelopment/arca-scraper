import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Ajuste para garantir que o Python ache a BaseScraper
try:
    from .base_scraper import BaseScraper
except ImportError:
    from base_scraper import BaseScraper

class GoodBomScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.url_teste = "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/produto/m/arroz-tp-1-oliron-5kg-19241"

    def rodar(self):
        print(f"🔍 Acessando GoodBom: {self.url_teste}")
        
        db = self.conectar()
        if db is None: return

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        try:
            # --- PARTE QUE FALTAVA: FAZER O DOWNLOAD ---
            resposta = requests.get(self.url_teste, headers=headers, timeout=10)
            if resposta.status_code != 200:
                print(f"❌ Erro HTTP: {resposta.status_code}")
                return
            
            soup = BeautifulSoup(resposta.text, 'html.parser')
            # -------------------------------------------

            # NOME
            nome_tag = soup.find('span', class_='product-name') or soup.find('h1')
            nome = nome_tag.text.strip() if nome_tag else "N/A"

            # PREÇO
            preco_tag = soup.find('span', class_='BcvAq')
            preco_valor = 0.0
            if preco_tag:
                preco_bruto = preco_tag.text.strip().split('/')[0]
                preco_valor = float(preco_bruto.replace('R$', '').replace('.', '').replace(',', '.').strip())

            # CÓDIGO DO PRODUTO
            codigo_tag = soup.find(lambda tag: tag.name == "span" and "Código:" in tag.text)
            codigo = codigo_tag.text.replace('Código: #', '').strip() if codigo_tag else "N/A"

            # MARCA
            marca_tag = soup.find(lambda tag: tag.name == "span" and "Marca:" in tag.text)
            marca = marca_tag.text.replace('Marca:', '').strip() if marca_tag else "N/A"

            # IMAGEM
            img_tag = soup.find('img', class_='product-image') or soup.find('img', alt=nome)
            url_img = img_tag['src'] if img_tag and img_tag.has_attr('src') else "N/A"

            produto = {
                "id_origem": codigo,
                "nome": nome,
                "marca": marca,
                "preco": preco_valor,
                "mercado": "GoodBom",
                "unidade": "Mogi Mirim",
                "url_imagem": url_img,
                "url_produto": self.url_teste,
                "data_extracao": datetime.now().isoformat(),
                "status": "raw"
            }

            print(f"✅ CAPTURA COMPLETA: {nome} | Código: {codigo} | Marca: {marca}")
            self.salvar_dados("precos_crus", [produto])

        except Exception as e:
            print(f"❌ Erro na extração detalhada: {e}")

if __name__ == "__main__":
    scraper = GoodBomScraper()
    scraper.rodar()