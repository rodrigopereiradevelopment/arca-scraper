import requests
import time
import re
import unicodedata
import os 
from datetime import datetime
from pymongo import UpdateOne
from scrapers.base_scraper import BaseScraper
from dotenv import load_dotenv 

# Carrega as variáveis do arquivo .env (Token e MongoDB)
load_dotenv()

def normalizar_nome(nome):
    if not nome: return "N/A"
    nome = unicodedata.normalize('NFKD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', nome).strip().upper()

class PontoNovoClient(BaseScraper):
    def __init__(self):
        super().__init__()
        self.api     = "https://api.mobilesim.com.br"
        self.mercado = "Ponto Novo"
        self.unidade = "Mogi Mirim"
        
        token = os.getenv("API_AUTHORIZATION_TOKEN")

<<<<<<< HEAD
        # Headers atualizados com 'isu' conforme exigência da API (Erro 401)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}", 
            "store": "90",
            "isu": "0",
            "platform": "1",
            "version": "v2.6.0"
        }
=======
        import os
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Agora o código busca o token do ambiente
token = os.getenv("API_AUTHORIZATION_TOKEN")

self.headers = {
    "User-Agent":    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Accept":        "application/json, text/plain, */*",
    "Origin":        "https://onlinesim.com.br",
    "Referer":       "https://onlinesim.com.br/",
    "Authorization": f"Bearer {token}",  # Usa o token carregado do .env
    "store":         "90",
    "isu":           "0",
    "platform":      "1",
    "version":       "v2.6.0"
}

>>>>>>> 12613532016be620dd40304f35473cff061b1137

    def get(self, url):
        try:
            res = requests.get(url, headers=self.headers, timeout=15)
            if res.status_code == 200:
                return res.json()
            # Se der erro 401 aqui, o Token no .env provavelmente expirou
            print(f"   ⚠️ Status {res.status_code} na URL: {url}")
        except Exception as e:
            print(f"   ❌ Erro de conexão: {e}")
        return None

    def executar(self):
        db = self.conectar()
        if db is None: 
            print("❌ Falha ao conectar ao Banco de Dados.")
            return

        print(f"🚀 {self.mercado}: Iniciando extração via API...")

        # Busca as Categorias Principais (Tabs)
        tabs_data = self.get(f"{self.api}/user/v1.02/tabs")
        
        if not tabs_data or not tabs_data.get("return"):
            print(f"❌ Erro na resposta inicial: {tabs_data}")
            return

        categorias = [
            c for c in tabs_data["return"]
            if not any(x in c["name"].upper() for x in ["INSUMOS", "CONSUMO"])
        ]

        for cat in categorias:
            cat_id, cat_nome = cat["id"], cat["name"]
            print(f"\n📦 Categoria: {cat_nome} (ID: {cat_id})")

            # Varrendo subcategorias de 0 a 15 (baseado no seu mapeamento manual)
            # Isso garante que pegamos o /7/1, /7/2, etc.
            for sub_id in range(0, 16):
                pagina = 0
                while True:
                    url_feed = f"{self.api}/user/v1.03/feed/{sub_id}/{pagina}/{cat_id}"
                    feed_data = self.get(url_feed)
                    
                    if not feed_data: break

                    ret = feed_data.get("return") or {}
                    produtos_raw = ret.get("products", [])
                    
                    # Se a página ou subcategoria não retornar produtos, para este loop
                    if not produtos_raw: break

                    batch_p, batch_h = [], []

                    for p in produtos_raw:
                        try:
                            # Lógica de Preço Inteligente (Preço Clube vs Preço Normal)
                            preco_base = float(p.get("price", 0))
                            oferta = p.get("offer") or {}
                            preco_oferta = float(oferta.get("offer_connect", preco_base))
                            
                            # Validação para não salvar preço zero
                            preco_final = preco_oferta if 0 < preco_oferta <= preco_base else preco_base
                            
                            id_origem = str(p.get("sku", ""))
                            if not id_origem or preco_final == 0: continue

                            nome_raw = p.get("name", "N/A")
                            img_hash = p.get("imghash", "")
                            url_img = f"https://s3.mobilesim.com.br/images/products/{img_hash}.jpg" if img_hash else ""

                            # Documento para a coleção 'produtos' (Upsert)
                            produto_doc = {
                                "id_origem": id_origem,
                                "ean": p.get("barcode", "N/A"),
                                "nome": nome_raw.upper(),
                                "nome_normalizado": normalizar_nome(nome_raw),
                                "categoria": cat_nome.upper(),
                                "subcategoria_id": sub_id,
                                "preco": preco_final,
                                "preco_antigo": preco_base if preco_final < preco_base else None,
                                "mercado": self.mercado,
                                "unidade": self.unidade,
                                "url_imagem": url_img,
                                "is_kg": p.get("is_kg", 0),
                                "data_extracao": datetime.now(),
                                "status": "bronze"
                            }

                            # Adiciona para escrita em lote (performance)
                            batch_p.append(UpdateOne(
                                {"id_origem": id_origem, "mercado": self.mercado},
                                {"$set": produto_doc}, upsert=True
                            ))
                            
                            # Documento para 'historico_precos' (Insert Always)
                            batch_h.append({
                                "id_origem": id_origem,
                                "preco": preco_final,
                                "mercado": self.mercado,
                                "data": datetime.now()
                            })

                        except Exception as e:
                            continue

                    # Salva no Banco de Dados se houver dados no lote
                    if batch_p:
                        db['produtos'].bulk_write(batch_p)
                        db['historico_precos'].insert_many(batch_h)
                        print(f"   ✅ SubID {sub_id} | Pág {pagina}: {len(batch_p)} produtos")

                    # Se a página veio com menos de 30 itens, é a última página daquela subcat
                    if len(produtos_raw) < 30: break
                    
                    pagina += 1
                    time.sleep(0.3) # Delay de segurança anti-bloqueio

        print("\n🏁 Ponto Novo: Atualização finalizada com sucesso!")

if __name__ == "__main__":
    PontoNovoClient().executar()