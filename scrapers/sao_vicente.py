"""
╔═══════════════════════════════════════════════════════════════════════════╗
║           PROJETO ARCA - Comparação de Preços                             ║
║                    Bot Acadêmico - São Vicente                            ║
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
import urllib3
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from scrapers.base_scraper import BaseScraper

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SaoVicenteScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.mercado = "São Vicente"
        self.unidade = "Mogi Mirim"
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

        self.max_workers = 5
        self.delay = 0.5

    # ────────────────────────────────────────
    # MÉTODOS AUXILIARES
    # ────────────────────────────────────────
    def buscar_ids(self, cgid, start, sz=50):
        """Busca lista de productIDs de uma categoria (paginado)"""
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
        """Busca detalhes de 1 produto via QuickView API"""
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
                elif res.status_code == 429:
                    wait = 5 * (i + 1)
                    print(f"      ⏱️ Rate limit pid={pid}, aguardando {wait}s...")
                    time.sleep(wait)
            except requests.exceptions.Timeout:
                print(f"      ⏱️ Timeout pid={pid} (tentativa {i+1}/{tentativas})")
                time.sleep(2 * (i + 1))
            except Exception as e:
                print(f"      ⚠️ Erro pid={pid}: {e}")
                break
        return None

    def parsear_produto(self, pid, data, nome_cat):
        """
        Extrai dados do JSON da QuickView e retorna:
        - produto (dict padronizado via BaseScraper)
        ou None se falhar
        """
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

            # ─── USA A NOVA BASE SCRAPER ───
            produto = BaseScraper.criar_produto(
                id_origem=pid,
                nome=nome_raw,
                preco=float(preco),
                marca=p.get("brand", "N/A"),
                categoria=nome_cat.upper(),
                mercado=self.mercado,
                unidade=self.unidade,
                url_imagem=url_img,
            )

            return produto

        except Exception:
            return None

    def buscar_produto_com_cat(self, args):
        """
        Wrapper para ThreadPoolExecutor.
        Recebe (pid, nome_cat), retorna produto ou None.
        """
        pid, nome_cat = args
        time.sleep(self.delay)

        data_prod = self.buscar_produto(pid)
        if not data_prod:
            return None

        return self.parsear_produto(pid, data_prod, nome_cat)

    # ────────────────────────────────────────
    # EXECUÇÃO PRINCIPAL
    # ────────────────────────────────────────
    def executar(self):
        db_mongo = self.conectar()
        if db_mongo is None:
            print("❌ Falha na conexão com MongoDB")
            return

        print(f"🚀 São Vicente: Iniciando extração paralela ({self.max_workers} threads)...")
        total_geral = 0

        for nome_cat, cgid in self.categorias.items():
            print(f"\n📦 Categoria: {nome_cat}")

            start     = 0
            total     = 1
            total_cat = 0

            while start < total:
                ids, total = self.buscar_ids(cgid, start)
                if not ids:
                    break

                print(f"   📋 {len(ids)} IDs | offset {start}/{total}")

                tarefas = [(pid, nome_cat) for pid in ids]

                batch_p = []  # ← REMOVI batch_h
                # batch_h = []  ← REMOVER

                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = {executor.submit(self.buscar_produto_com_cat, t): t for t in tarefas}

                    for future in as_completed(futures):
                        produto = future.result()
                        if not produto:
                            continue

                        batch_p.append(self.criar_upsert_produto(produto))
                        # ← REMOVI batch_h.append(historico)

                if batch_p:
                    db_mongo['produtos'].bulk_write(batch_p)
                    # ← REMOVI self.salvar_historico(db_mongo, batch_h)
                    total_cat  += len(batch_p)
                    total_geral += len(batch_p)
                    print(f"   ✅ Salvos: {len(batch_p)} produtos")

                start += len(ids)
                time.sleep(1)

            print(f"   📊 Total {nome_cat}: {total_cat} produtos")

        self.fechar()
        print(f"\n🏁 São Vicente: Concluído! Total geral: {total_geral} produtos")


if __name__ == "__main__":
    scraper = SaoVicenteScraper()
    print("\n--- 🛒 Iniciando Coleta: São Vicente ---")
    inicio = time.time()
    try:
        scraper.executar()
        duracao = int(time.time() - inicio)
        print(f"⏱️ Tempo total: {timedelta(seconds=duracao)}")
        print("✅ Processo finalizado com sucesso!")
    except Exception as e:
        print(f"❌ Erro durante a execução: {e}")