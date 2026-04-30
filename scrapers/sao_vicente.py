"""
╔═══════════════════════════════════════════════════════════════════════════╗
║           PROJETO ARCA - Comparação de Preços                             ║
║                    Bot Acadêmico                                          ║
╠═══════════════════════════════════════════════════════════════════════════╣
║ Este bot coleta preços para TCC na ETEC Pedro Ferreira Alves              ║
║ Objetivo: acessibilidade no consumo e ciência de dados                    ║
║ Não há intenção de sobrecarregar servidores.                              ║
║                                                                           ║
║ Desenvolvedor : Rodrigo                                                   ║
║ GitHub        : https://github.com/rodrigopereiradevelopment/arca-ionic   ║
║ Contato       : rodrigopereira.development@gmail.com                      ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
import requests
import time
import re
import urllib3
from datetime import datetime
from pymongo import UpdateOne
from scrapers.base_scraper import BaseScraper

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def normalizar_nome(nome):
    import unicodedata
    nome = unicodedata.normalize('NFKD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', nome).strip().upper()


class SaoVicenteScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.grid_url      = "https://www.svicente.com.br/on/demandware.store/Sites-SaoVicente-Site/pt_BR/Search-UpdateGrid"
        self.quickview_url = "https://www.svicente.com.br/on/demandware.store/Sites-SaoVicente-Site/pt_BR/Product-ShowQuickView"

        self.headers = {
            "User-Agent": (
                "ARCA-Bot/1.0 (Bot Academico TCC ETEC; "
                "Contato: rodrigopereira.development@gmail.com; "
                "GitHub: https://github.com/rodrigopereiradevelopment/arca-ionic)"
            ),
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/html, */*",
            "Referer": "https://www.svicente.com.br"
        }

        self.categorias = {
            "Mercearia":             "012",
            "Bebidas":               "002",
            "Bebidas Alcoolicas":    "003",
            "Hortifruti":            "010",
            "Carnes Aves Peixes":    "005",
            "Frios Laticinios":      "008",
            "Congelados":            "006",
            "Higiene Beleza":        "009",
            "Limpeza":               "011",
            "Biscoitos Salgadinhos": "004",
            "Doces Sobremesas":      "007",
            "Padaria":               "015",
            "Saudaveis Organicos":   "016",
            "Bazar Utilidades":      "001",
            "Mundo Pet":             "014",
        }

    def buscar_ids(self, cgid, start, sz=50):
        params = {
            "cgid":  cgid,
            "start": str(start),
            "sz":    str(sz),
            "srule": "Price Ascending"
        }
        try:
            res = requests.get(
                self.grid_url,
                headers=self.headers,
                params=params,
                timeout=20,
                verify=False
            )
            if res.status_code == 200:
                data  = res.json()
                ids   = [p["productID"] for p in data.get("productSearch", {}).get("productIds", [])]
                total = data.get("productSearch", {}).get("count", 0)
                return ids, total
        except Exception as e:
            print(f"   ❌ Erro ao buscar IDs: {e}")
        return [], 0

    def buscar_produto(self, pid, tentativas=3):
        for i in range(tentativas):
            try:
                res = requests.get(
                    self.quickview_url,
                    headers=self.headers,
                    params={"pid": pid},
                    timeout=15,
                    verify=False
                )
                if res.status_code == 200:
                    return res.json()
            except requests.exceptions.Timeout:
                print(f"      ⏱️ Timeout pid={pid} (tentativa {i+1}/{tentativas})")
                time.sleep(2 * (i + 1))
            except Exception as e:
                print(f"      ⚠️ Erro pid={pid}: {e}")
                break
        return None

    def parsear_produto(self, data, nome_cat):
        try:
            p = data.get("product", {})

            nome_raw = p.get("productName", "")
            if not nome_raw:
                return None

            preco = p.get("price", {}).get("sales", {}).get("value", 0.0)
            if not preco:
                return None

            imagens = p.get("images", {}).get("large", [])
            url_img = imagens[0].get("absURL", "") if imagens else ""

            return {
                "id_origem":        p.get("id", "N/A"),
                "nome":             nome_raw.upper(),
                "nome_normalizado": normalizar_nome(nome_raw),
                "marca":            p.get("brand", "N/A"),
                "categoria":        nome_cat.upper(),
                "preco":            float(preco),
                "mercado":          "São Vicente",
                "unidade":          "Mogi Mirim",
                "url_imagem":       url_img,
                "data_extracao":    datetime.now(),
                "status":           "bronze"
            }
        except Exception:
            return None

    def executar(self):
        db_mongo = self.conectar()
        if db_mongo is None:
            print("❌ Falha na conexão com MongoDB") # Adicione esse print para debug
            return

        print("🚀 São Vicente: Iniciando extração (QuickView JSON)...")
        total_geral = 0

        for nome_cat, cgid in self.categorias.items():
            print(f"\n📦 Categoria: {nome_cat}")

            start        = 0
            total        = 1
            total_cat    = 0

            while start < total:
                ids, total = self.buscar_ids(cgid, start)
                if not ids:
                    break

                print(f"   📋 {len(ids)} IDs | offset {start}/{total}")

                batch_p = []
                batch_h = []

                for pid in ids:
                    data_prod = self.buscar_produto(pid)
                    if not data_prod:
                        continue

                    produto = self.parsear_produto(data_prod, nome_cat)
                    if not produto:
                        continue

                    batch_p.append(UpdateOne(
                        {"id_origem": pid, "mercado": "São Vicente"},
                        {"$set": produto},
                        upsert=True
                    ))
                    batch_h.append({
                        "id_origem": pid,
                        "preco":     produto["preco"],
                        "mercado":   "São Vicente",
                        "data":      datetime.now()
                    })

                    time.sleep(0.25) # Delay para evitar block

                if batch_p:
                    db_mongo['produtos'].bulk_write(batch_p)
                    db_mongo['historico_precos'].insert_many(batch_h)
                    total_cat  += len(batch_p)
                    total_geral += len(batch_p)
                    print(f"   ✅ Salvos: {len(batch_p)} produtos")

                start += len(ids)
                time.sleep(1) # Delay entre páginas

            print(f"   📊 Total {nome_cat}: {total_cat} produtos")

        self.client.close() 
        print(f"\n🏁 São Vicente: Concluído! Total geral: {total_geral} produtos")
        
    # Pra rodar manual ou automatico    
if __name__ == "__main__":
    scraper = SaoVicenteScraper()
    print("\n--- 🛒 Iniciando Coleta: São Vicente ---")
    try:
        scraper.executar()
        print("✅ Processo finalizado com sucesso!")
    except Exception as e:
        print(f"❌ Erro durante a execução: {e}")
