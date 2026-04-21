import requests
import time
from datetime import datetime
from scrapers.base_scraper import BaseScraper

class PagueMenosScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.db = self.conectar()
        self.colecao = "precos_crus"
        # Headers completos para evitar o bloqueio (Simulando Desktop)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9",
            "Referer": "https://www.superpaguemenos.com.br/",
            "Origin": "https://www.superpaguemenos.com.br",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

    def rodar_extracao(self):
        if self.db is None:
            print("❌ Erro: Banco de dados não conectado. Verifique seu .env!")
            return

        total_produtos = 16832
        offset = 0
        passo = 50 

        print(f"🚀 [ARCA] Iniciando Pague Menos: {total_produtos} itens alvo.")

        while offset < total_produtos:
            # Endpoint oficial de busca da VTEX
            url = f"https://www.superpaguemenos.com.br/api/catalog_system/pub/products/search?_from={offset}&_to={offset + passo - 1}"
            
            try:
                print(f"📡 Solicitando itens {offset} até {offset + passo}...")
                response = requests.get(url, headers=self.headers, timeout=20)
                
                # Verificação de segurança antes de tentar ler o JSON
                content_type = response.headers.get('Content-Type', '')
                
                if response.status_code == 200 and 'application/json' in content_type:
                    dados_vtex = response.json()
                    
                    if not dados_vtex:
                        print("🏁 Fim dos dados na API.")
                        break

                    lote_formatado = []
                    for produto in dados_vtex:
                        try:
                            items = produto.get('items', [])
                            if not items: continue
                            
                            oferta = items[0].get('sellers', [{}])[0].get('commertialOffer', {})
                            preco = oferta.get('Price', 0)

                            if preco > 0:
                                lote_formatado.append({
                                    "id_origem": produto.get('productId'),
                                    "nome": produto.get('productName'),
                                    "preco": preco,
                                    "mercado": "Pague Menos",
                                    "unidade": "Mogi Mirim",
                                    "url_produto": produto.get('link'),
                                    "imagem": items[0].get('images', [{}])[0].get('imageUrl') if items[0].get('images') else None,
                                    "data_extracao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "status": "cru"
                                })
                        except Exception:
                            continue

                    if lote_formatado:
                        self.salvar_dados(self.colecao, lote_formatado)
                    
                    offset += passo
                    time.sleep(2) # Delay um pouco maior para segurança
                
                else:
                    if 'text/html' in content_type:
                        print("🚫 Bloqueio detectado: O servidor retornou HTML em vez de JSON.")
                        print("Dica: Pode ser um Captcha ou bloqueio de IP. Tente trocar de rede (Wi-Fi/4G).")
                    else:
                        print(f"⚠️ Resposta inesperada (Status {response.status_code}).")
                    
                    break # Para o loop para não queimar o IP

            except Exception as e:
                print(f"❌ Erro no loop: {e}")
                time.sleep(10)

if __name__ == "__main__":
    scraper = PagueMenosScraper()
    scraper.rodar_extracao()
