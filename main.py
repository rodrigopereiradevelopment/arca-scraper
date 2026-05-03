import time
from datetime import timedelta
from datetime import datetime

from scrapers.goodbom import GoodBomScraper
from scrapers.paguemenos import PagueMenosScraper
from scrapers.imperial import ImperialScraper
from scrapers.atacadao import AtacadaoScraper
from scrapers.ponto_novo import PontoNovoScraper
from scrapers.sao_vicente import SaoVicenteScraper

from limpeza_silver import processar_e_salvar_mongodb


def executar_pipeline_arca():
    inicio_geral = time.time()
    data_hora_inicio = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    print(f"--- 🚀 INICIANDO PIPELINE ARCA: {data_hora_inicio} ---")

    # ─── ATACADÃO PRIMEIRO (mais sensível) ───
    mercados = [
        {"nome": "Atacadão",    "instancia": AtacadaoScraper()},   # ← PRIMEIRO!
        {"nome": "São Vicente", "instancia": SaoVicenteScraper()},
        {"nome": "Pague Menos", "instancia": PagueMenosScraper()},
        {"nome": "Ponto Novo",  "instancia": PontoNovoScraper()},
        {"nome": "Imperial",    "instancia": ImperialScraper()},
        {"nome": "GoodBom",     "instancia": GoodBomScraper()},
    ]

    tempos = []
    erros = []

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
            print(f"❌ ERRO EM {nome}: {e}")
            erros.append(nome)
            tempos.append((nome, 0))
            
            # Se o Atacadão falhar, CONTINUA pros outros
            if nome == "Atacadão":
                print("⚠️ Atacadão falhou, mas continuando com os demais scrapers...")
                continue

    # ─── RELATÓRIO DE DESEMPENHO ───
    fim_geral = time.time()
    tempo_total_segundos = int(fim_geral - inicio_geral)
    
    print("\n" + "=" * 40)
    print("📊 RELATÓRIO DE PERFORMANCE DO ARCA")
    print("=" * 40)
    for nome, duracao in tempos:
        percentual = (duracao / tempo_total_segundos) * 100 if tempo_total_segundos > 0 else 0
        status = "❌ FALHOU" if nome in erros else "✅"
        print(f"{nome.ljust(15)}: {timedelta(seconds=int(duracao))} ({percentual:.1f}%) {status}")
    
    print("-" * 40)
    print(f"Tempo Total de Execução: {timedelta(seconds=tempo_total_segundos)}")
    
    if erros:
        print(f"⚠️  {len(erros)} scraper(s) falharam: {', '.join(erros)}")
    else:
        print("✅ Todos os scrapers concluídos com sucesso!")
    print("=" * 40)

    # ─── ETAPA 2: LIMPEZA SILVER ───
    print("\n--- 🧹 INICIANDO LIMPEZA E PADRONIZAÇÃO (CAMADA SILVER) ---")
    try:
        processar_e_salvar_mongodb()
        print("🎉 Camada Silver atualizada com sucesso pelo pipeline!")
    except Exception as e:
        print(f"❌ Erro ao executar a limpeza Silver: {e}")

    # ─── RESUMO FINAL ───
    print("\n" + "=" * 40)
    print("🏁 PIPELINE ARCA CONCLUÍDO")
    print(f"   Início: {data_hora_inicio}")
    print(f"   Fim:    {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"   Total:  {timedelta(seconds=tempo_total_segundos)}")
    print("=" * 40)


if __name__ == "__main__":
    executar_pipeline_arca()