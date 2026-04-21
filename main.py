import sys
from datetime import datetime
# Importando todos os scrapers da sua pasta
from scrapers.goodbom import processar_banco as run_goodbom
from scrapers.paguemenos import processar_paguemenos as run_paguemenos
from scrapers.imperial import ImperialScraper
from scrapers.atacadao import AtacadaoScraper
from scrapers.ponto_novo import PontoNovoScraper  # Ajuste o nome da classe se for diferente
from scrapers.sao_vicente import SaoVicenteScraper # Ajuste o nome da classe se for diferente

def executar_pipeline_arca():
    inicio = datetime.now()
    print(f"--- 🚀 INICIANDO PIPELINE ARCA: {inicio.strftime('%d/%m/%Y %H:%M:%S')} ---")

    # Lista de tarefas para facilitar a manutenção
    # [Nome, Função/Método para executar]
    
    # 1. GOODBOM
    print("\n[1/6] Processando GoodBom...")
    try: run_goodbom()
    except Exception as e: print(f"⚠️ Erro no GoodBom: {e}")

    # 2. PAGUE MENOS (O que terminamos agora!)
    print("\n[2/6] Processando Pague Menos...")
    try: run_paguemenos()
    except Exception as e: print(f"⚠️ Erro no Pague Menos: {e}")

    # 3. IMPERIAL
    print("\n[3/6] Processando Imperial...")
    try:
        sc_imp = ImperialScraper()
        sc_imp.executar()
    except Exception as e: print(f"⚠️ Erro no Imperial: {e}")

    # 4. ATACADÃO
    print("\n[4/6] Processando Atacadão...")
    try:
        sc_ata = AtacadaoScraper()
        sc_ata.executar()
    except Exception as e: print(f"⚠️ Erro no Atacadão: {e}")

    # 5. PONTO NOVO
    print("\n[5/6] Processando Ponto Novo...")
    try:
        sc_ponto = PontoNovoScraper()
        sc_ponto.executar()
    except Exception as e: print(f"⚠️ Erro no Ponto Novo: {e}")

    # 6. SÃO VICENTE
    print("\n[6/6] Processando São Vicente...")
    try:
        sc_sv = SaoVicenteScraper()
        sc_sv.executar()
    except Exception as e: print(f"⚠️ Erro no São Vicente: {e}")

    # Finalização
    fim = datetime.now()
    duracao = fim - inicio
    print(f"\n--- ✅ PIPELINE FINALIZADO EM: {duracao} ---")
    print(f"Total de mercados processados: 6")

if __name__ == "__main__":
    executar_pipeline_arca()