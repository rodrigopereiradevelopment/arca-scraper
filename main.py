import sys
from datetime import datetime
# Note que agora importamos as funções/classes que já cuidam do próprio banco
from scrapers.goodbom import processar_banco as run_goodbom
from scrapers.imperial import ImperialScraper
from scrapers.atacadao import AtacadaoScraper

def executar_pipeline_arca():
    inicio = datetime.now()
    print(f"--- 🚀 INICIANDO PIPELINE ARCA: {inicio.strftime('%d/%m/%Y %H:%M:%S')} ---")

    try:
        # 1. GOODBOM: Ele lê o SQLite arca.db e salva no Mongo (App + Histórico)
       # print("\n[1/3] Processando GoodBom (via SQLite/HTML)...")
        #run_goodbom()

        # 2. IMPERIAL: Puxa direto da API e salva no Mongo (App + Histórico)
        #print("\n[2/3] Processando Imperial (via API REST)...")
       # scraper_imp = ImperialScraper()
       # scraper_imp.executar()

        # 3. ATACADÃO: Puxa via GraphQL e faz Bulk Write (App + Histórico)
        print("\n[3/3] Processando Atacadão (via GraphQL)...")
        scraper_ata = AtacadaoScraper()
        scraper_ata.executar()

        fim = datetime.now()
        print(f"\n--- ✅ PIPELINE FINALIZADO EM: {fim - inicio} ---")

    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO NO PIPELINE: {e}")
        sys.exit(1)

if __name__ == "__main__":
    executar_pipeline_arca()