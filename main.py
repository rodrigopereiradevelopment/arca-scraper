import sys
from datetime import datetime
# Importando os scrapers
from scrapers.goodbom import processar_banco as run_goodbom
from scrapers.imperial import ImperialScraper
from scrapers.atacadao import AtacadaoScraper

def executar_pipeline_arca():
    inicio = datetime.now()
    print(f"--- 🚀 INICIANDO PIPELINE ARCA: {inicio.strftime('%d/%m/%Y %H:%M:%S')} ---")

    try:
        # 1. GOODBOM
        print("\n[1/3] Processando GoodBom (via SQLite/HTML)...")
        try:
            run_goodbom()
        except Exception as e:
            print(f"⚠️ Erro no GoodBom, mas seguindo adiante: {e}")

        # 2. IMPERIAL
        print("\n[2/3] Processando Imperial (via API REST)...")
        try:
            scraper_imp = ImperialScraper()
            # O if/else agora está dentro do try e bem alinhado
            if hasattr(scraper_imp, 'testar_conexao') and scraper_imp.testar_conexao(): 
                scraper_imp.executar()
            else:
                # Se ainda não criou o método testar_conexao, ele executa direto
                scraper_imp.executar()
        except Exception as e:
            print(f"❌ Falha no Imperial: {e}. Indo para o próximo...")

        # 3. ATACADÃO
        print("\n[3/3] Processando Atacadão (via GraphQL)...")
        try:
            scraper_ata = AtacadaoScraper()
            scraper_ata.executar() 
        except Exception as e:
            print(f"❌ Atacadão deu erro, mas o pipeline continua: {e}")

        # Finalização (fora dos blocos try internos, mas dentro do principal)
        fim = datetime.now()
        print(f"\n--- ✅ PIPELINE FINALIZADO EM: {fim - inicio} ---")

    except Exception as e:
        # Esse só pega se algo travar o script inteiro
        print(f"\n❌ ERRO CRÍTICO NO PIPELINE: {e}")
        sys.exit(1)

if __name__ == "__main__":
    executar_pipeline_arca()