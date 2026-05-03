"""
╔═══════════════════════════════════════════════════════════════════════════╗
║            PROJETO ARCA - Comparação de Preços                            ║
║                   Bot Acadêmico - GoodBom                                 ║
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
import re
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from scrapers.base_scraper import BaseScraper


class GoodBomScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.mercado  = "GoodBom"
        self.unidade  = "Mogi Mirim"
        self.base_url = "https://goodbom.com.br/pt/goodbom-mogi-mirim-sp"

        self.headers = {
            "User-Agent": (
                "ARCA-Bot/1.0 (Bot Academico TCC ETEC; "
                "Contato: rodrigopereira.development@gmail.com; "
                "GitHub: https://github.com/rodrigopereiradevelopment/arca-ionic)"
            ),
            "RSC": "1"
        }

        self.categorias = [
            "hortifrutigranjeiro-1",
            "acougue-47",
            "mercearia-3",
            "frios-e-laticinios-9",
            "padaria-50",
            "pet-shop-14",
            "peixaria-82",
            "magazine-16",
            "promocoes-99999",
        ]

        self.max_workers = 3
        self.delay_pagina = 1

    # ────────────────────────────────────────
    # MÉTODOS AUXILIARES
    # ────────────────────────────────────────
    def buscar_pagina(self, slug, pagina):
        url = f"{self.base_url}/{slug}?page={pagina}"
        try:
            res = requests.get(url, headers=self.headers, timeout=20)
            if res.status_code == 200:
                return res.text
            print(f"   ⚠️ {res.status_code} → {url}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")
        return None

    def parsear(self, texto, slug):
        return re.findall(
            r'"EcommerceProduct","id":"(\d+)"[^}]*?"name":"([^"]+)"[^}]*?"slug":"([^"]*)"[^}]*?"image":"([^"]*)"[^}]*?"price":([\d.]+)[^}]*?"priceWithDiscount":([\d.]+)',
            texto
        )

    def processar_categoria(self, slug):
        """Processa uma categoria inteira — usado pelo ThreadPoolExecutor."""
        cat_nome = slug.rsplit("-", 1)[0].upper().replace("-", " ")
        print(f"\n📦 Categoria: {cat_nome}")

        pagina = 1
        total_cat = 0
        batch_p = []
        batch_h = []

        while True:
            texto = self.buscar_pagina(slug, pagina)
            if not texto:
                break

            produtos_raw = self.parsear(texto, slug)
            if not produtos_raw:
                break

            for pid, nome_raw, produto_slug, img, preco_str, desconto_str in produtos_raw:
                try:
                    preco_base  = float(preco_str)
                    preco_desc  = float(desconto_str)
                    preco_final = preco_desc if preco_desc > 0 else preco_base

                    if preco_final == 0:
                        continue

                    # Decodificar nome com escape unicode
                    try:
                        nome_limpo = nome_raw.encode().decode('unicode_escape')
                    except Exception:
                        nome_limpo = nome_raw

                    # ─── USA A NOVA BASE SCRAPER ───
                    produto = BaseScraper.criar_produto(
                        id_origem=pid,
                        nome=nome_limpo,
                        preco=preco_final,
                        preco_original=preco_base if preco_desc > 0 else None,
                        categoria=cat_nome,
                        mercado=self.mercado,
                        unidade=self.unidade,
                        url_imagem=img,
                        url_produto=f"https://goodbom.com.br/pt/goodbom-mogi-mirim-sp/{produto_slug}",
                    )

                    batch_p.append(self.criar_upsert_produto(produto))
                    batch_h.append(self.criar_historico(pid, preco_final, self.mercado))

                except Exception:
                    continue

            total_cat += len(produtos_raw)
            print(f"   📄 {cat_nome} | Pág {pagina}: {len(produtos_raw)} produtos")

            if len(produtos_raw) < 30:
                break

            pagina += 1
            time.sleep(self.delay_pagina)

        print(f"   🏁 {cat_nome}: {total_cat} produtos coletados")
        return cat_nome, batch_p, batch_h, total_cat

    # ────────────────────────────────────────
    # EXECUÇÃO PRINCIPAL
    # ────────────────────────────────────────
    def executar(self):
        db = self.conectar()
        if db is None:
            return

        print(f"🚀 GoodBom: Iniciando extração paralela ({self.max_workers} categorias simultâneas)...")
        total_geral = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.processar_categoria, slug): slug for slug in self.categorias}

            for future in as_completed(futures):
                try:
                    cat_nome, batch_p, batch_h, total_cat = future.result()

                    if batch_p:
                        db['produtos'].bulk_write(batch_p)
                        self.salvar_historico(db, batch_h)
                        total_geral += total_cat
                        print(f"   💾 {cat_nome}: {total_cat} produtos salvos no MongoDB")

                except Exception as e:
                    slug = futures[future]
                    print(f"   ❌ Erro na categoria {slug}: {e}")

        self.fechar()
        print(f"\n🏁 Good Bom: Concluído! Total geral: {total_geral} produtos")


if __name__ == "__main__":
    scraper = GoodBomScraper()
    print("\n--- 🛒 Iniciando Coleta: Good Bom ---")
    inicio = time.time()
    try:
        scraper.executar()
        duracao = int(time.time() - inicio)
        print(f"⏱️ Tempo total: {timedelta(seconds=duracao)}")
        print("✅ Processo finalizado com sucesso!")
    except Exception as e:
        print(f"❌ Erro durante a execução: {e}")