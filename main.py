import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pymongo import MongoClient
from dotenv import load_dotenv

from scrapers.goodbom import GoodBomScraper
from scrapers.imperial import ImperialScraper
from scrapers.atacadao import AtacadaoScraper

load_dotenv()

def iniciar_conexao():
    uri = os.getenv("MONGO_URI")
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        return client
    except Exception as e:
        print(f"❌ ERRO DE CONEXÃO: {e}")
        return None

def executar_bot():
    cliente = iniciar_conexao()
    if not cliente: return

    db = cliente["arca_bronze"]
    colecao = db["precos"]

    # -----------------------------------------------
    # GOODBOM — requests, paralelo com ThreadPool
    # -----------------------------------------------
    urls_goodbom = [
        "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/produto/m/manteiga-extra-csal-catupiry-200g-7366",
        "https://www.goodbom.com.br/goodbom-mogi-mirim-sp/produto/m/acucar-refuniao-1kg-5769",
    ]

    print(f"\n🛒 GoodBom — {len(urls_goodbom)} produtos em paralelo...")
    scraper_goodbom = GoodBomScraper()

    with ThreadPoolExecutor(max_workers=3) as executor:
        futuros = {
            executor.submit(scraper_goodbom.extrair, url): url
            for url in urls_goodbom
        }
        for futuro in as_completed(futuros):
            dados = futuro.result()
            if dados:
                try:
                    colecao.insert_one(dados)
                    print(f"✅ {dados['nome']} (GoodBom) | R$ {dados['preco']} salvo!")
                except Exception as e:
                    print(f"❌ Erro ao salvar GoodBom: {e}")
            else:
                print(f"⚠️ Falha: {futuros[futuro]}")

    # -----------------------------------------------
    # IMPERIAL — Playwright, sequencial
    # -----------------------------------------------
    urls_imperial = [
        "https://onlinesim.com.br/supermercadoimperial/details/7897517209650",
    ]

    print(f"\n🛒 Imperial — {len(urls_imperial)} produtos...")
    scraper_imperial = ImperialScraper()

    for url in urls_imperial:
        print(f"🚀 ImperialScraper extraindo: {url}")
        dados = scraper_imperial.extrair(url)
        if dados:
            try:
                colecao.insert_one(dados)
                print(f"✅ {dados['nome']} (Imperial) | R$ {dados['preco']} salvo!")
            except Exception as e:
                print(f"❌ Erro ao salvar Imperial: {e}")

    # -----------------------------------------------
    # ATACADÃO — Playwright + BaseScraper (salva internamente)
    # -----------------------------------------------
    urls_atacadao = [
        "https://www.atacadao.com.br/arroz-camil-agulhinha---tipo-1-pacote-com-5kg-12658-13743/p",
    ]

    print(f"\n🛒 Atacadão — {len(urls_atacadao)} produtos...")
    scraper_atacadao = AtacadaoScraper()

    for url in urls_atacadao:
        scraper_atacadao.scrape(url)

    cliente.close()
    print("\n✅ Extração concluída!")

if __name__ == "__main__":
    executar_bot()