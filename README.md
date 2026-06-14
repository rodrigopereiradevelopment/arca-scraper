# 🕷️ ARCA Scraper — Coleta de Preços

[![Pipeline Status](https://github.com/rodrigopereiradevelopment/arca-scraper/actions/workflows/main.yml/badge.svg)](https://github.com/rodrigopereiradevelopment/arca-scraper/actions/workflows/main.yml)
[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org/)

O **ARCA Scraper** é o módulo de coleta de dados do ecossistema ARCA. Ele captura preços de **6 redes de supermercados** de Mogi Mirim/SP, armazena em MongoDB Atlas e sincroniza com Supabase PostgreSQL para o app mobile.

> 🔗 **App Mobile:** [arca-ionic](https://github.com/rodrigopereiradevelopment/arca-ionic)
> 🚀 **API Backend:** [arca-next](https://github.com/rodrigopereiradevelopment/arca-next)

---

## 🏪 Mercados Monitorados

| Mercado | Método | Produtos | Tempo (paralelo) |
|---------|--------|----------|------------------|
| **Atacadão** | GraphQL API | ~8.400 | ~4 min |
| **São Vicente** | API Demandware | ~13.200 | ~56 min |
| **Pague Menos** | HTML Parsing | ~16.200 | ~20 min |
| **Ponto Novo** | API REST (MobileSim) | ~5.200 | ~15 min |
| **Imperial** | API REST (MobileSim) | ~3.100 | ~12 min |
| **GoodBom** | HTML Parsing (Regex) | ~11.100 | ~32 min |
| **TOTAL** | | **~57.000** | **~56 min** ⚡ |

---

## 🧠 Arquitetura de Dados

```
GitHub Actions (Matrix Strategy — 6 jobs paralelos)
       │
       ▼
6 Scrapers (ThreadPoolExecutor)
       │
       ▼
MongoDB Atlas (arca_bronze — 53k documentos)
  ├── nome_normalizado (já padronizado)
  ├── preco_atual
  ├── historico_precos (array embutido)
  ├── total_coletas
  └── menor/maior_preco_historico
       │
       ▼ (ETL — migrate_to_supabase.py)
       │
Supabase PostgreSQL (Gold)
       │
       ▼
arca-next (API) → arca-ionic (App Mobile)
```

---

## ⚡ Performance (Otimizações)

### Pipeline Completo (GitHub Actions)

| Métrica | Antes | Depois | Economia |
|---------|-------|--------|----------|
| Scraping (sequencial) | 200 min | **56 min** (paralelo) | **-72%** |
| Sync Supabase | 72 min | **15 min** (paralelo) | **-79%** |
| **Pipeline total** | **272 min** | **71 min** | **-74%** |

### Técnicas utilizadas

- `ThreadPoolExecutor` para paralelismo interno (3-10 workers)
- `bulk_write` no MongoDB (lotes de 50-1000)
- **Matrix strategy** no GitHub Actions (6 jobs paralelos)
- Normalização centralizada na `BaseScraper`
- Histórico embutido no documento (eliminou coleção separada)

### MongoDB: Antes vs Depois

| Item | Antes | Depois | Redução |
|------|-------|--------|---------|
| Coleções | 3 (produtos + historico + silver) | **1** (produtos) | **-67%** |
| Documentos | ~424k (53k + 371k) | **53k** | **-87%** |
| Espaço | ~250 MB | **18 MB** | **-93%** |

---

## 🛠️ Stack Tecnológica

- **Linguagem:** Python 3.12
- **Banco de Dados:** MongoDB Atlas (Cloud NoSQL) + Supabase PostgreSQL
- **Bibliotecas:** `requests`, `pymongo`, `beautifulsoup4`, `ftfy`, `supabase`, `python-dotenv`
- **CI/CD:** GitHub Actions (matrix strategy, seg/qui 00:00 BRT)
- **Dev:** Linux Mint

---

## 🚀 Instalação e Uso

```bash
git clone https://github.com/rodrigopereiradevelopment/arca-scraper.git
cd arca-scraper
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Crie `.env` na raiz:

```env
# MongoDB
MONGO_URI=mongodb+srv://<USUARIO>:<SENHA>@arca-cluster.xo5yomu.mongodb.net/

# Tokens dos scrapers
IMPERIAL_TOKEN=seu_token_aqui
API_AUTHORIZATION_TOKEN=seu_token_aqui

# Supabase (opcional, para sync)
SUPABASE_URL=https://seuprojeto.supabase.co
SUPABASE_SERVICE_KEY=sua_service_key_aqui
```

```bash
# Todos os mercados (sequencial — local)
python main.py

# Um mercado específico
python main.py --mercado atacadao

# Mercados disponíveis
python main.py --mercado sao_vicente
python main.py --mercado pague_menos
python main.py --mercado ponto_novo
python main.py --mercado imperial
python main.py --mercado goodbom

# Sync com Supabase
python scripts/migrate_to_supabase.py --sync
```

---

## 📁 Estrutura

```
arca-scraper/
├── scrapers/
│   ├── base_scraper.py       # Classe mãe (histórico embutido, normalização)
│   ├── atacadao.py           # GraphQL (104 subcategorias, paralelo)
│   ├── sao_vicente.py        # API Demandware (15 categorias, paralelo)
│   ├── paguemenos.py         # HTML parsing (13 categorias)
│   ├── goodbom.py            # Regex parsing (9 categorias, paralelo)
│   ├── imperial.py           # API MobileSim
│   └── ponto_novo.py         # API MobileSim
├── scripts/
│   ├── migrate_to_supabase.py   # Migração MongoDB → Supabase
│   └── sync_mercado.py          # Sync paralelo por mercado
├── main.py                   # Orquestrador (suporta --mercado)
├── requirements.txt
└── .github/workflows/
    └── main.yml              # CI/CD (matrix strategy)
```

---

## 🔄 Pipeline Automatizado (GitHub Actions)

```yaml
jobs:
  scraping:           # 6 máquinas paralelas (56 min)
    strategy:
      matrix:
        mercado: [atacadao, sao_vicente, pague_menos, ponto_novo, imperial, goodbom]

  sync_supabase:      # 6 máquinas paralelas (15 min)
    needs: scraping
    strategy:
      matrix:
        mercado: [atacadao, sao_vicente, pague_menos, ponto_novo, imperial, goodbom]
```

- **Schedule:** Segunda e Quinta às 00:00 BRT
- **Manual:** Botão "Run workflow" no GitHub
- **Notificação:** Discord webhook em caso de falha
- **Tempo total:** ~71 minutos

---

## 📈 Evolução do Projeto

| Versão | Característica | Tempo | Espaço |
|--------|----------------|-------|--------|
| v1.0 | Sequencial + Silver | ~5h45 | ~250 MB |
| v2.0 | Paralelismo interno | ~3h20 | ~250 MB |
| v3.0 | Matrix strategy + Histórico embutido | ~71 min | 18 MB |

---

## ⚠️ Aviso Ético e Legal

Este projeto foi desenvolvido para fins educacionais como Trabalho de Conclusão de Curso (TCC) na ETEC Pedro Ferreira Alves.

- ✅ Respeita intervalos de requisição (`time.sleep`)
- ✅ User-Agent identificado como bot acadêmico
- ✅ Dados coletados são de domínio público
- ✅ Sem intenção de sobrecarregar servidores

---

## 👨‍🎓 Equipe

TCC — ETEC Pedro Ferreira Alves — Mogi Mirim/SP — 2025/2026

| Nome | Papel |
|------|-------|
| Rodrigo Pereira | Desenvolvedor Full Stack |
| Bruno Henrique Oliveira Capra | Desenvolvedor |
| Miguel da Silva Bernades | Desenvolvedor |
| Felix Renato Marques Junior | Desenvolvedor |

**Orientador:** Prof. Maurício Aparecido das Neves
**Coordenadora:** Prof.ª Simone Andreia de Campos Camargo

📝 **Licença:** MIT
