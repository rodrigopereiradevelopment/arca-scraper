import requests
import re
from datetime import datetime

class GoodBomScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Rsc": "1" 
        }

    def extrair(self, url_produto):
        try:
            response = requests.get(url_produto, headers=self.headers, timeout=15)
            response.encoding = 'utf-8'
            if response.status_code != 200:
                print(f"⚠️ Erro HTTP {response.status_code} no GoodBom")
                return None

            texto = response.text
            
            # --- EXTRAÇÃO COM REGEX ---
            id_origem = re.search(r'"code":"(.*?)"', texto)
            nome = re.search(r'"product":{.*?"name":"(.*?)"', texto)
            marca = re.search(r'"brand":"(.*?)"', texto)
            url_img = re.search(r'"image":"(.*?)"', texto)
            categoria = re.search(r'"category":"(.*?)"', texto)

            # --- LÓGICA DE PREÇO PROTEGIDA (O FIX DO AÇÚCAR) ---
            match_desconto = re.search(r'"priceWithDiscount":\s*([\d.]+)', texto)
            match_normal = re.search(r'"price":\s*([\d.]+)', texto)

            preco_final = 0.0
            
            # Se tem desconto e ele é maior que zero, usa ele
            if match_desconto and float(match_desconto.group(1)) > 0:
                preco_final = float(match_desconto.group(1))
            # Se não, usa o preço normal
            elif match_normal:
                preco_final = float(match_normal.group(1))

            # --- TRATAMENTO DE STRING ---
            nome_limpo = nome.group(1) if nome else "N/A"
            # Remove escapes de JSON (ex: \u002F para /)
            nome_limpo = nome_limpo.encode().decode('unicode_escape').upper()

            return {
                "id_origem": id_origem.group(1) if id_origem else "N/A",
                "nome": nome_limpo,
                "marca": marca.group(1) if marca else "N/A",
                "categoria": categoria.group(1).upper() if categoria else "GERAL",
                "preco": preco_final,
                "mercado": "GoodBom",
                "unidade": "Mogi Mirim",
                "url_imagem": url_img.group(1) if url_img else "N/A",
                "url_produto": url_produto,
                "data_extracao": datetime.now().isoformat(),
                "status": "raw"
            }

        except Exception as e:
            print(f"❌ Erro no Scraper GoodBom: {e}")
            return None

if __name__ == "__main__":
    # Teste rápido com o Açúcar União (que estava vindo zero)
    url_teste = "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/produto/m/acucar-refuniao-1kg-5769"
    scraper = GoodBomScraper()
    resultado = scraper.extrair(url_teste)
    if resultado:
        print(f"✅ SUCESSO: {resultado['nome']} | R$ {resultado['preco']:.2f}")