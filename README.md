# 🛒 ARCA - Comparação de Preços (Mogi Mirim)

[![Pipeline Status](https://github.com/rodrigopereiradevelopment/arca-scraper/actions/workflows/main.yml/badge.svg)](https://github.com/rodrigopereiradevelopment/arca-scraper/actions/workflows/main.yml)

O **ARCA** é um ecossistema de captura e análise de dados focado no varejo de Mogi Mirim. O objetivo é centralizar preços de **6 grandes redes de supermercados**, permitindo uma comparação precisa para o consumidor final.

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

## 🧠 Arquitetura de Dados (Refatorada)
┌─────────────────────────────────────────────────────────────────────┐
│ GitHub Actions │
│ (Matrix Strategy - 6 jobs paralelos) │
└─────────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────┐
│ 6 Scrapers (ThreadPool) │
│ Cada mercado roda em uma máquina virtual isolada │
└─────────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────┐
│ MongoDB Atlas (arca_bronze) │
│ │
│ produtos (53.633 documentos) │
│ ├── nome_normalizado (já padronizado!) │
│ ├── preco_atual │
│ ├── historico_precos (array embutido) ← HISTÓRICO DENTRO DO PRODUTO│
│ ├── total_coletas │
│ ├── menor_preco_historico │
│ └── maior_preco_historico │
└─────────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────┐
│ Supabase (PostgreSQL) │
│ Sincronização paralela por mercado │
└─────────────────────────────────────────────────────────────────────┘
│
▼
┌─────────────────────────────────────────────────────────────────────┐
│ arca-ionic (App Mobile) │
│ Ionic + Angular + Leaflet │
└─────────────────────────────────────────────────────────────────────┘

text

### ✨ Principais Decisões Técnicas

| Decisão | Benefício |
|---------|-----------|
| **Histórico embutido no produto** | Redução de 371k documentos para 53k (~87% menos espaço) |
| **Remoção da camada Silver** | Eliminou duplicação de dados e simplificou pipeline |
| **Matrix strategy no GitHub** | 6 máquinas paralelas → tempo total de 3h20 para **56min** |
| **Sync paralelo por mercado** | Sync de 72min para **~15min** |

---

## ⚡ Performance (Otimizações)

### Scrapers Individuais

| Scraper | Antes | Depois | Ganho |
|---------|-------|--------|-------|
| **Atacadão** | 1h30 | **4min** | **-95%** |
| **São Vicente** | 3h00 | **56min** | **-69%** |
| **GoodBom** | 1h00 | **32min** | **-47%** |

### Pipeline Completo (GitHub Actions)

| Métrica | Antes | Depois | Economia |
|---------|-------|--------|----------|
| Scraping (sequencial) | 200 min | **56 min** (paralelo) | **-72%** |
| Sync Supabase | 72 min | **15 min** (paralelo) | **-79%** |
| **Pipeline total** | **272 min** | **71 min** | **-74%** |

**Técnicas utilizadas:**
- `ThreadPoolExecutor` para paralelismo interno (3-10 workers)
- `bulk_write` no MongoDB (lotes de 50-1000)
- **Matrix strategy** no GitHub Actions (6 jobs paralelos)
- Normalização centralizada na `BaseScraper`
- Histórico embutido (eliminou coleção separada)

---

## 🗄️ MongoDB: Antes vs Depois

| Item | Antes | Depois | Redução |
|------|-------|--------|---------|
| Coleções | 3 (produtos + historico + silver) | **1** (produtos) | **-67%** |
| Documentos | ~424k (53k + 371k) | **53k** | **-87%** |
| Espaço | ~250 MB | **18 MB** | **-93%** |
| Alertas MongoDB | ⚠️ Espaço crítico | ✅ All good! | ✅ |

---

## 🛠️ Stack Tecnológica

- **Linguagem:** Python 3.12
- **Banco de Dados:** MongoDB Atlas (Cloud NoSQL)
- **Cache/API:** Supabase (PostgreSQL)
- **Bibliotecas:** `requests`, `pymongo`, `beautifulsoup4`, `ftfy`, `supabase`, `python-dotenv`
- **CI/CD:** GitHub Actions (matrix strategy, schedule semanal)
- **Dev:** Linux Mint (Desktop) + Termux (Mobile)

---

## 🚀 Instalação e Uso

### 1. Clonar o repositório

```bash
git clone https://github.com/rodrigopereiradevelopment/arca-scraper.git
cd arca-scraper

```

### 2. Criar ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

```

### 3. Configurar .env
Crie um arquivo .env na raiz do projeto:

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

### 4. Executar

```bash
# Todos os mercados (sequencial - local)
python main.py

# Um mercado específico (usado pelo GitHub Actions)
python main.py --mercado atacadao

# Sync com Supabase
python scripts/migrate_to_supabase.py --sync

```

### 📊 Estrutura do Projeto

```text
arca-scraper/
├── scrapers/
│   ├── base_scraper.py      # Classe mãe (histórico embutido, normalização)
│   ├── atacadao.py          # GraphQL (104 subcategorias, paralelo)
│   ├── sao_vicente.py       # API Demandware (15 categorias, paralelo)
│   ├── paguemenos.py        # HTML parsing (13 categorias)
│   ├── goodbom.py           # Regex parsing (9 categorias, paralelo)
│   ├── imperial.py          # API MobileSim
│   └── ponto_novo.py        # API MobileSim
├── scripts/
│   ├── migrate_to_supabase.py  # Migração MongoDB → Supabase
│   └── sync_mercado.py         # Sync paralelo por mercado
├── main.py                  # Orquestrador (suporta --mercado)
├── requirements.txt
└── .github/workflows/
    └── main.yml             # CI/CD (matrix strategy, seg/qui 00:00 BRT)

```

### 🔄 Pipeline Automatizado (GitHub Actions)
O GitHub Actions executa com matrix strategy:

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

## Schedule: Segunda e Quinta às 00:00 BRT

## Manual: Botão "Run workflow" no GitHub

## Tempo total: ~71 minutos

### 📈 Evolução do Projeto
Versão	Característica	Tempo	Espaço
v1.0	Sequencial + Silver	~5h45	~250 MB
v2.0	Paralelismo interno	~3h20	~250 MB
v3.0	Matrix strategy + Histórico embutido	~71 min	18 MB

### ⚠️ Aviso Ético e Legal
Este projeto foi desenvolvido para fins educacionais como Trabalho de Conclusão de Curso (TCC) na ETEC Pedro Ferreira Alves.

✅ Respeita intervalos de requisição (time.sleep)

✅ User-Agent identificado como bot acadêmico

✅ Dados coletados são de domínio público

✅ Sem intenção de sobrecarregar servidores

###📄 Licença
Este projeto está sob a licença MIT — veja o arquivo LICENSE para detalhes.

### 👤 Autor
# Rodrigo Pereira
# GitHub: @rodrigopereiradevelopment
# Contato: rodrigopereira.development@gmail.com
# Projeto relacionado: arca-ionic (App Mobile)

### 🙏 Agradecimentos
# ETEC Pedro Ferreira Alves (TCC)

# Orientador Prof. Maurício Aparecido das Neves

# Colegas de turma: Bruno, Miguel, Félix

# Comunidade open-source pelo suporte!
