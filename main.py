import time
from datetime import datetime, timedelta

from scrapers.goodbom import GoodBomScraper
from scrapers.paguemenos import PagueMenosScraper
from scrapers.imperial import ImperialScraper
from scrapers.atacadao import AtacadaoScraper
from scrapers.ponto_novo import PontoNovoScraper
from scrapers.sao_vicente import SaoVicenteScraper

def executar_pipeline_arca():
    inicio_geral = time.time()
    data_hora_inicio = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    print(f"--- 🚀 INICIANDO PIPELINE ARCA: {data_hora_inicio} ---")

    mercados = [
        # Coloque os mais rápidos primeiro para garantir os dados essenciais cedo
        {"nome": "São Vicente", "instancia": SaoVicenteScraper()},
        {"nome": "Pague Menos", "instancia": PagueMenosScraper()},
        {"nome": "Atacadão",    "instancia": AtacadaoScraper()},
        {"nome": "Ponto Novo",  "instancia": PontoNovoScraper()},
        {"nome": "Imperial",    "instancia": ImperialScraper()},
        {"nome": "GoodBom",     "instancia": GoodBomScraper()}, # O maratonista por último
    ]

    tempos = []

    for item in mercados:
        nome = item["nome"]
        bot = item["instancia"]
        
        print(f"\n⏱️  Iniciando {nome}...")
        inicio_bot = time.time()
        
        try:
            bot.executar()
            fim_bot = time.time()
            duracao = fim_bot - inicio_bot
            tempos.append((nome, duracao))
            print(f"✅ {nome} finalizado em {timedelta(seconds=int(duracao))}")
        except Exception as e:
            print(f"❌ Erro em {nome}: {e}")
            tempos.append((nome, 0))

    # --- RELATÓRIO DE DESEMPENHO ---
    fim_geral = time.time()
    tempo_total_segundos = int(fim_geral - inicio_geral)
    
    print("\n" + "="*40)
    print("📊 RELATÓRIO DE PERFORMANCE DO ARCA")
    print("="*40)
    for nome, duracao in tempos:
        percentual = (duracao / tempo_total_segundos) * 100 if tempo_total_segundos > 0 else 0
        print(f"{nome.ljust(15)}: {timedelta(seconds=int(duracao))} ({percentual:.1f}%)")
    
    print("-" * 40)
    print(f"Tempo Total de Execução: {timedelta(seconds=tempo_total_segundos)}")
    print("="*40)

if __name__ == "__main__":
    executar_pipeline_arca()