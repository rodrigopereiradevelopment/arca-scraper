import time
from datetime import timedelta, datetime
import requests  # 👈 ADICIONAR
import os  # 👈 ADICIONAR

from scrapers.goodbom import GoodBomScraper
from scrapers.paguemenos import PagueMenosScraper
from scrapers.imperial import ImperialScraper
from scrapers.atacadao import AtacadaoScraper
from scrapers.ponto_novo import PontoNovoScraper
from scrapers.sao_vicente import SaoVicenteScraper


def sync_com_supabase():
    """Chama o endpoint de sync do Next.js para atualizar preços no Supabase"""
    try:
        api_url = os.getenv("NEXT_PUBLIC_APP_URL", "http://localhost:3000")
        sync_secret = os.getenv("SYNC_SECRET")
        
        if not sync_secret:
            print("⚠️ SYNC_SECRET não configurado. Pulando sync com Supabase.")
            return
        
        print("\n🔄 Sincronizando preços com Supabase...")
        response = requests.post(
            f"{api_url}/api/migrate",
            json={"action": "sync", "secret": sync_secret},
            timeout=7200  # 2 horas, para garantir que o sync completo seja realizado sem timeout
        )
        
        if response.status_code == 200:
            dados = response.json()
            print(f"✅ Sync concluído: {dados.get('sincronizados', 0)} preços atualizados")
        else:
            print(f"⚠️ Sync falhou: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Erro ao chamar sync: {e}")


def executar_pipeline_arca():
    inicio_geral = time.time()
    data_hora_inicio = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    print(f"--- 🚀 INICIANDO PIPELINE ARCA: {data_hora_inicio} ---")
    print("📌 Modo: Histórico embutido + Sync Supabase")

    # ─── ATACADÃO PRIMEIRO (mais sensível) ───
    mercados = [
        {"nome": "Atacadão",    "instancia": AtacadaoScraper()},
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

    # ─── PIPELINE CONCLUÍDO - SEM SILVER ───
    print("\n✅ Pipeline concluído - Histórico embutido nos produtos")
    print("   (Sem etapa de limpeza Silver - economia de espaço e tempo)")

    # ─── NOVO: Sincronizar com Supabase ───
    sync_com_supabase()

    # ─── RESUMO FINAL ───
    print("\n" + "=" * 40)
    print("🏁 PIPELINE ARCA CONCLUÍDO")
    print(f"   Início: {data_hora_inicio}")
    print(f"   Fim:    {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"   Total:  {timedelta(seconds=tempo_total_segundos)}")
    print("=" * 40)


if __name__ == "__main__":
    executar_pipeline_arca()